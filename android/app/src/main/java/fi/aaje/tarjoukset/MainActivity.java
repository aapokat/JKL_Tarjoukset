package fi.aaje.tarjoukset;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * The app is the same page as the website, opened in a WebView, plus what a website cannot do:
 * favourites that stay, background checks and phone notifications (OfferWorker).
 * The page talks to the app through window.TarjousApp (see Bridge below).
 */
public class MainActivity extends Activity {
    static final String SITE = "https://aapokat.github.io/JKL_Tarjoukset/";
    static final String HOST = "aapokat.github.io";

    private WebView web;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // favourites, alerts and settings live in localStorage
        s.setUserAgentString(s.getUserAgentString() + " JklTarjouksetApp/" + BuildConfig.VERSION_NAME);
        s.setSupportMultipleWindows(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.addJavascriptInterface(new Bridge(), "TarjousApp");
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest req) {
                Uri u = req.getUrl();
                if (HOST.equals(u.getHost()) && u.getPath() != null && u.getPath().startsWith("/JKL_Tarjoukset")) return false;
                openOutside(u);   // store pages open in the phone's browser
                return true;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest req, WebResourceError err) {
                if (!req.isForMainFrame()) return;
                view.loadDataWithBaseURL(null, OFFLINE, "text/html", "utf-8", null);
            }
        });

        if (saved != null) web.restoreState(saved);
        else web.loadUrl(SITE + hashFor(getIntent()));

        askNotificationPermission();
        OfferWorker.schedule(this);
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        String hash = hashFor(intent);
        if (!hash.isEmpty()) web.loadUrl(SITE + hash);
    }

    /** A tap on a notification opens the matching view: "#hits" for alert hits, "#fav" for saved offers. */
    private static String hashFor(Intent intent) {
        String v = intent == null ? null : intent.getStringExtra("view");
        return v == null ? "" : "#" + v;
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    @SuppressWarnings("deprecation")
    public void onBackPressed() {
        // First let the page close an open drawer; then go back in the page's history; then leave.
        web.evaluateJavascript("window.appBack ? String(window.appBack()) : 'false'", handled -> {
            if ("\"true\"".equals(handled)) return;
            if (web.canGoBack()) web.goBack();
            else MainActivity.super.onBackPressed();
        });
    }

    private void openOutside(Uri u) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, u));
        } catch (Exception ignored) {
        }
    }

    private void askNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);
        }
    }

    private static final String OFFLINE = "<!doctype html><meta name=viewport content='width=device-width'>"
            + "<body style='font:16px sans-serif;background:#F1F2F4;color:#18191C;display:grid;place-items:center;height:90vh;text-align:center'>"
            + "<div><h2>Ei yhteyttä</h2><p>Tarjousten lataus ei onnistunut.</p>"
            + "<p><a href='" + SITE + "' style='display:inline-block;background:#18191C;color:#fff;padding:12px 22px;border-radius:99px;text-decoration:none'>Yritä uudelleen</a></p></div>";

    /** Methods the page can call as window.TarjousApp.*. They run on a background thread. */
    private class Bridge {
        /** The page sends its alerts, saved offers, chosen stores and interests whenever they change. */
        @JavascriptInterface
        public void sync(String json) {
            SharedPreferences p = getSharedPreferences(OfferWorker.PREFS, MODE_PRIVATE);
            String old = p.getString("state", "");
            p.edit().putString("state", json).apply();
            if (!json.equals(old)) OfferWorker.checkSoon(MainActivity.this);
        }

        @JavascriptInterface
        public void testNotification() {
            OfferWorker.testNotification(MainActivity.this);
        }

        @JavascriptInterface
        public boolean notificationsAllowed() {
            return Build.VERSION.SDK_INT < 33
                    || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
        }

        @JavascriptInterface
        public void askNotifications() {
            runOnUiThread(MainActivity.this::askNotificationPermission);
        }

        @JavascriptInterface
        public String version() {
            return BuildConfig.VERSION_NAME;
        }
    }
}
