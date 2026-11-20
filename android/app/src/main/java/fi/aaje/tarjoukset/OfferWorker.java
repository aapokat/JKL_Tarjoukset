package fi.aaje.tarjoukset;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;

import androidx.annotation.NonNull;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import androidx.work.Constraints;
import androidx.work.ExistingPeriodicWorkPolicy;
import androidx.work.ExistingWorkPolicy;
import androidx.work.NetworkType;
import androidx.work.OneTimeWorkRequest;
import androidx.work.PeriodicWorkRequest;
import androidx.work.WorkManager;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Runs every few hours in the background: downloads the same offers.json as the page and notifies about
 * 1) offers that match the user's alerts (each offer once),
 * 2) new offers like the ones the user often looks at (only offers that were not in the previous download),
 * 3) saved offers that end today or tomorrow.
 * Everything stays on the phone; there is no server.
 */
public class OfferWorker extends Worker {
    static final String PREFS = "tarjoukset";
    private static final String CH_ALERTS = "vahdit", CH_TIPS = "suositukset", CH_SAVED = "tallennetut";

    public OfferWorker(@NonNull Context c, @NonNull WorkerParameters p) {
        super(c, p);
    }

    static void schedule(Context c) {
        Constraints net = new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
        PeriodicWorkRequest every = new PeriodicWorkRequest.Builder(OfferWorker.class, 3, TimeUnit.HOURS)
                .setConstraints(net).build();
        WorkManager.getInstance(c).enqueueUniquePeriodicWork("offers", ExistingPeriodicWorkPolicy.KEEP, every);
    }

    /** After the user changes alerts or interests: check once soon, so a new alert answers right away. */
    static void checkSoon(Context c) {
        Constraints net = new Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build();
        OneTimeWorkRequest once = new OneTimeWorkRequest.Builder(OfferWorker.class)
                .setInitialDelay(20, TimeUnit.SECONDS).setConstraints(net).build();
        WorkManager.getInstance(c).enqueueUniqueWork("offers-now", ExistingWorkPolicy.REPLACE, once);
    }

    // ---------- the check

    @NonNull
    @Override
    public Result doWork() {
        Context c = getApplicationContext();
        SharedPreferences p = c.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        try {
            JSONObject state = new JSONObject(p.getString("state", "{}"));
            List<Offer> offers = load();
            Set<String> chosen = strings(state.optJSONArray("stores"));
            File knownFile = new File(c.getFilesDir(), "known.txt");
            Set<String> known = readSet(knownFile);
            boolean first = known.isEmpty();

            // 1) alerts
            JSONArray watches = state.optJSONArray("watches");
            Set<String> seenW = readSet(new File(c.getFilesDir(), "seen-alerts.txt"));
            List<String> alertLines = new ArrayList<>();
            int alertHits = 0;
            if (watches != null) {
                for (Offer o : offers) {
                    if (!o.inStores(chosen)) continue;
                    for (int i = 0; i < watches.length(); i++) {
                        JSONObject w = watches.optJSONObject(i);
                        if (w == null || !o.matches(w)) continue;
                        String k = w.optString("t") + ":" + w.optString("v") + "|" + o.id;
                        if (seenW.add(k)) {
                            alertHits++;
                            if (alertLines.size() < 6) alertLines.add(o.line());
                        }
                        break;
                    }
                }
            }
            writeSet(new File(c.getFilesDir(), "seen-alerts.txt"), seenW, 4000);

            // 2) new offers like the ones the user looks at
            List<String> tipLines = new ArrayList<>();
            int tipHits = 0;
            JSONArray interests = state.optJSONArray("interests");
            if (!first && interests != null && interests.length() > 0 && state.optBoolean("tips", true)) {
                for (Offer o : offers) {
                    if (known.contains(o.id) || !o.inStores(chosen) || o.pct < 30) continue;
                    if (o.likes(interests)) {
                        tipHits++;
                        if (tipLines.size() < 6) tipLines.add(o.line());
                    }
                }
            }
            Set<String> now = new HashSet<>();
            for (Offer o : offers) now.add(o.id);
            writeSet(knownFile, now, 20000);

            // 3) saved offers that are ending
            JSONArray favs = state.optJSONArray("favs");
            Set<String> warned = readSet(new File(c.getFilesDir(), "seen-ending.txt"));
            List<String> endLines = new ArrayList<>();
            if (favs != null) {
                for (int i = 0; i < favs.length(); i++) {
                    JSONObject f = favs.optJSONObject(i);
                    if (f == null) continue;
                    int days = daysLeft(f.optString("valid"));
                    if ((days == 0 || days == 1) && warned.add(f.optString("id") + "|" + days)) {
                        endLines.add(f.optString("name") + (days == 0 ? ": päättyy tänään" : ": päättyy huomenna"));
                    }
                }
            }
            writeSet(new File(c.getFilesDir(), "seen-ending.txt"), warned, 1000);

            if (alertHits > 0) notify(c, 1, CH_ALERTS, alertHits == 1 ? "Vahti löysi tarjouksen" : "Vahdit löysivät " + alertHits + " tarjousta",
                    alertLines, alertHits, "hits");
            if (tipHits > 0) notify(c, 2, CH_TIPS, tipHits == 1 ? "Uusi ale sinua kiinnostavista tuotteista" : tipHits + " uutta alea sinua kiinnostavista tuotteista",
                    tipLines, tipHits, "tips");
            if (!endLines.isEmpty()) notify(c, 3, CH_SAVED, endLines.size() == 1 ? "Tallennettu tarjous päättyy pian" : endLines.size() + " tallennettua tarjousta päättyy pian",
                    endLines, endLines.size(), "fav");
            p.edit().putLong("lastCheck", System.currentTimeMillis()).apply();
            return Result.success();
        } catch (Exception e) {
            return getRunAttemptCount() < 3 ? Result.retry() : Result.failure();
        }
    }

    private static List<Offer> load() throws Exception {
        HttpURLConnection con = (HttpURLConnection) new URL(MainActivity.SITE + "offers.json").openConnection();
        con.setConnectTimeout(20000);
        con.setReadTimeout(60000);
        con.setRequestProperty("Cache-Control", "no-cache");
        StringBuilder sb = new StringBuilder();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(con.getInputStream(), StandardCharsets.UTF_8))) {
            char[] buf = new char[65536];
            int n;
            while ((n = r.read(buf)) > 0) sb.append(buf, 0, n);
        } finally {
            con.disconnect();
        }
        JSONObject d = new JSONObject(sb.toString());
        JSONArray stores = d.getJSONArray("stores"), cats = d.getJSONArray("cats"), rows = d.getJSONArray("offers");
        JSONArray subs = d.optJSONArray("subs");
        List<Offer> out = new ArrayList<>();
        for (int i = 0; i < rows.length(); i++) {
            JSONArray r = rows.getJSONArray(i);
            Offer o = new Offer();
            JSONArray si = r.getJSONArray(0);
            for (int j = 0; j < si.length(); j++) o.stores.add(stores.getJSONObject(si.getInt(j)).getString("name"));
            int ci = r.getInt(1);
            o.cat = cats.optString(ci);
            o.name = r.optString(2);
            o.price = r.isNull(3) ? 0 : r.optDouble(3, 0);
            o.pct = r.isNull(6) ? 0 : r.optInt(6, 0);
            o.note = r.isNull(7) ? "" : r.optString(7);
            o.valid = r.isNull(8) ? "" : r.optString(8);
            o.pid = r.isNull(11) ? "" : r.optString(11);
            o.brand = r.isNull(12) ? "" : r.optString(12);
            int sub = r.length() > 15 && !r.isNull(15) ? r.optInt(15, -1) : -1;
            if (sub >= 0 && subs != null && subs.optJSONArray(ci) != null) o.sub = subs.optJSONArray(ci).optString(sub);
            if (daysLeft(o.valid) < 0) continue;   // ended
            // The same id as the page uses for favourites: [pid || name, price, note].join("|")
            o.id = (o.pid.isEmpty() ? o.name : o.pid) + "|" + num(r, 3) + "|" + o.note;
            o.key = norm(o.name + " " + o.brand + " " + String.join(" ", o.stores));
            out.add(o);
        }
        return out;
    }

    /** JavaScript's String(number): 2.5 -> "2.5", 3.0 -> "3", null -> "". */
    private static String num(JSONArray r, int i) {
        if (r.isNull(i)) return "";
        double v = r.optDouble(i, 0);
        if (v == Math.rint(v)) return String.valueOf((long) v);
        return String.valueOf(v);
    }

    static final class Offer {
        final List<String> stores = new ArrayList<>();
        String id, key, cat = "", sub = "", name = "", note = "", valid = "", pid = "", brand = "";
        double price;
        int pct;

        boolean inStores(Set<String> chosen) {
            if (chosen.isEmpty()) return true;
            for (String s : stores) if (chosen.contains(s)) return true;
            return false;
        }

        /** The same rules as matches() on the page. */
        boolean matches(JSONObject w) {
            String t = w.optString("t"), v = w.optString("v");
            String store = w.optString("store", "");
            if (!store.isEmpty() && !stores.contains(store)) return false;
            double max = w.optDouble("max", 0);
            if (max > 0 && !(price > 0 && price <= max)) return false;
            int minPct = w.optInt("minPct", 0);
            if (minPct > 0 && pct < minPct) return false;
            switch (t) {
                case "q":
                    for (String part : norm(v).split("\\s+")) if (!part.isEmpty() && !key.contains(part)) return false;
                    return !norm(v).trim().isEmpty();
                case "brand": {
                    String b = norm(v), n = norm(name);
                    return norm(brand).equals(b) || n.startsWith(b + " ") || n.contains(" " + b + " ");
                }
                case "cat":
                    return cat.equals(v);
                case "store":
                    return stores.contains(v);
                case "pid":
                    return pid.equals(v) || (!w.optString("label").isEmpty() && norm(name).equals(norm(w.optString("label"))));
                default:
                    return false;
            }
        }

        boolean likes(JSONArray interests) {
            for (int i = 0; i < interests.length(); i++) {
                JSONObject x = interests.optJSONObject(i);
                if (x == null) continue;
                String t = x.optString("t"), v = x.optString("v");
                if ("sub".equals(t) && cat.equals(x.optString("cat")) && sub.equals(v)) return true;
                if ("cat".equals(t) && cat.equals(v)) return true;
                if ("brand".equals(t) && !brand.isEmpty() && norm(brand).equals(norm(v))) return true;
            }
            return false;
        }

        String line() {
            String where = stores.size() == 1 ? stores.get(0) : stores.size() + " kauppaa";
            String p = price > 0 ? String.format(Locale.forLanguageTag("fi-FI"), "%.2f €", price) : "";
            return name + "  " + (pct > 0 ? "−" + pct + " %" : "") + (p.isEmpty() ? "" : ", " + p) + ", " + where;
        }
    }

    // ---------- helpers

    static String norm(String s) {
        String n = Normalizer.normalize(s == null ? "" : s.toLowerCase(Locale.ROOT), Normalizer.Form.NFKD);
        return n.replaceAll("\\p{M}", "");
    }

    private static final Pattern DATE = Pattern.compile("(\\d{1,2})\\.(\\d{1,2})\\.(\\d{4})?");

    /** Days until the last date in "Voimassa 15.11. asti" / "19.11.–22.11.": 0 = ends today, -1 = ended, 99 = no date. */
    static int daysLeft(String valid) {
        Matcher m = DATE.matcher(valid == null ? "" : valid);
        String d = null, mo = null, y = null;
        while (m.find()) {
            d = m.group(1);
            mo = m.group(2);
            y = m.group(3);
        }
        if (d == null) return 99;
        Calendar today = Calendar.getInstance();
        today.set(Calendar.HOUR_OF_DAY, 0);
        today.set(Calendar.MINUTE, 0);
        today.set(Calendar.SECOND, 0);
        today.set(Calendar.MILLISECOND, 0);
        Calendar end = (Calendar) today.clone();
        end.set(Calendar.YEAR, y != null ? Integer.parseInt(y) : today.get(Calendar.YEAR));
        end.set(Calendar.MONTH, Integer.parseInt(mo) - 1);
        end.set(Calendar.DAY_OF_MONTH, Integer.parseInt(d));
        long diff = Math.round((end.getTimeInMillis() - today.getTimeInMillis()) / 86400000.0);
        if (y == null && diff > 180) diff -= end.getActualMaximum(Calendar.DAY_OF_YEAR);
        if (y == null && diff < -180) diff += today.getActualMaximum(Calendar.DAY_OF_YEAR);
        return (int) diff;
    }

    private static Set<String> strings(JSONArray a) {
        Set<String> out = new HashSet<>();
        if (a != null) for (int i = 0; i < a.length(); i++) out.add(a.optString(i));
        return out;
    }

    private static Set<String> readSet(File f) {
        Set<String> out = new HashSet<>();
        if (!f.exists()) return out;
        try (BufferedReader r = new BufferedReader(new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) if (!line.isEmpty()) out.add(line);
        } catch (Exception ignored) {
        }
        return out;
    }

    private static void writeSet(File f, Set<String> set, int max) {
        try (FileOutputStream out = new FileOutputStream(f)) {
            int n = 0;
            StringBuilder sb = new StringBuilder();
            for (String s : set) {
                if (n++ >= max) break;
                sb.append(s.replace('\n', ' ')).append('\n');
            }
            out.write(sb.toString().getBytes(StandardCharsets.UTF_8));
        } catch (Exception ignored) {
        }
    }

    private static void channels(Context c) {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager nm = c.getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(CH_ALERTS, "Hintavahdit", NotificationManager.IMPORTANCE_HIGH));
        nm.createNotificationChannel(new NotificationChannel(CH_TIPS, "Sinua kiinnostavat alet", NotificationManager.IMPORTANCE_DEFAULT));
        nm.createNotificationChannel(new NotificationChannel(CH_SAVED, "Tallennetut tarjoukset", NotificationManager.IMPORTANCE_DEFAULT));
    }

    private static void notify(Context c, int id, String channel, String title, List<String> lines, int total, String view) {
        channels(c);
        Intent open = new Intent(c, MainActivity.class).putExtra("view", view)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pi = PendingIntent.getActivity(c, id, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        NotificationCompat.InboxStyle box = new NotificationCompat.InboxStyle();
        for (String l : lines) box.addLine(l);
        if (total > lines.size()) box.setSummaryText("ja " + (total - lines.size()) + " muuta");
        NotificationCompat.Builder b = new NotificationCompat.Builder(c, channel)
                .setSmallIcon(R.drawable.ic_stat)
                .setColor(0xFFE5372B)
                .setContentTitle(title)
                .setContentText(lines.isEmpty() ? "" : lines.get(0))
                .setStyle(box)
                .setNumber(total)
                .setAutoCancel(true)
                .setContentIntent(pi);
        try {
            NotificationManagerCompat.from(c).notify(id, b.build());
        } catch (SecurityException ignored) {
            // notifications not allowed
        }
    }

    static void testNotification(Context c) {
        List<String> l = new ArrayList<>();
        l.add("Tältä ilmoitus näyttää, kun vahti löytää tarjouksen.");
        notify(c, 9, CH_ALERTS, "Ilmoitukset toimivat", l, 1, "hits");
    }
}
