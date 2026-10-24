package se.eidhaart.rundeck.icons;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.content.res.XmlResourceParser;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/* Coverage check: shows which of your installed apps get a RunDeck icon automatically,
   and lets you copy the exact names of the rest so the pack can be updated. */
public class MainActivity extends Activity {
    static final int RED = Color.parseColor("#ff1238"), CYAN = Color.parseColor("#1fe3f0"), BG = Color.parseColor("#070a13"), DIM = Color.parseColor("#aaa4b6");

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        Set<String> matched = new HashSet<>();
        try {
            XmlResourceParser x = getResources().getXml(R.xml.appfilter);
            int ev;
            while ((ev = x.next()) != XmlResourceParser.END_DOCUMENT) {
                if (ev == XmlResourceParser.START_TAG && "item".equals(x.getName())) {
                    String c = x.getAttributeValue(null, "component");
                    if (c != null) matched.add(c);
                }
            }
        } catch (Exception e) { }
        Map<String, String> byPkg = new HashMap<>();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(getAssets().open("packages.txt")))) {
            String l; while ((l = r.readLine()) != null) { String[] p = l.split("\\|"); if (p.length >= 2) byPkg.put(p[0], p[1]); }
        } catch (Exception e) { }

        PackageManager pm = getPackageManager();
        Intent i = new Intent(Intent.ACTION_MAIN); i.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> apps = pm.queryIntentActivities(i, 0);
        List<String> ok = new ArrayList<>(), fix = new ArrayList<>(), none = new ArrayList<>();
        StringBuilder copy = new StringBuilder();
        for (ResolveInfo ri : apps) {
            String pkg = ri.activityInfo.packageName, act = ri.activityInfo.name;
            if (pkg.equals(getPackageName())) continue;
            String label = String.valueOf(ri.loadLabel(pm)), comp = "ComponentInfo{" + pkg + "/" + act + "}";
            if (matched.contains(comp)) ok.add(label);
            else if (byPkg.containsKey(pkg)) { fix.add(label); copy.append(label).append(" | ").append(comp).append(" | ").append(byPkg.get(pkg)).append('\n'); }
            else { none.add(label); copy.append(label).append(" | ").append(comp).append(" | NEW\n"); }
        }
        Collections.sort(ok); Collections.sort(fix); Collections.sort(none);
        final String text = copy.toString();

        ScrollView sv = new ScrollView(this); sv.setBackgroundColor(BG);
        LinearLayout col = new LinearLayout(this); col.setOrientation(LinearLayout.VERTICAL); int pad = dp(20); col.setPadding(pad, pad * 2, pad, pad);
        sv.addView(col);
        col.addView(tv("RUNDECK // ICON PACK", 22, RED, true));
        col.addView(tv("Apply it in your launcher settings (Icon pack → RunDeck Icons).", 14, DIM, false));
        col.addView(tv("\n✓ " + ok.size() + " apps matched automatically", 16, CYAN, true));
        col.addView(tv("~ " + fix.size() + " have an icon but need their exact name. You can pick them by hand in the launcher meanwhile.", 14, DIM, false));
        col.addView(tv("+ " + none.size() + " have no icon yet", 14, DIM, false));
        Button btn = new Button(this); btn.setText("Copy list to send for the next update"); btn.setTextColor(BG); btn.setBackgroundColor(RED);
        btn.setOnClickListener(v -> { ((ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("RunDeck icons", text)); Toast.makeText(this, "Copied", Toast.LENGTH_SHORT).show(); });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2); lp.topMargin = dp(16); lp.bottomMargin = dp(16); col.addView(btn, lp);
        section(col, "Needs exact name", fix); section(col, "No icon yet", none); section(col, "Matched", ok);
        setContentView(sv);
    }
    void section(LinearLayout col, String title, List<String> items) {
        if (items.isEmpty()) return;
        col.addView(tv("\n" + title.toUpperCase(), 13, RED, true));
        col.addView(tv(String.join("\n", items), 14, Color.WHITE, false));
    }
    TextView tv(String s, int sp, int color, boolean mono) {
        TextView t = new TextView(this); t.setText(s); t.setTextSize(sp); t.setTextColor(color); t.setLineSpacing(0, 1.15f);
        if (mono) t.setTypeface(Typeface.MONOSPACE, Typeface.BOLD); t.setGravity(Gravity.START); return t;
    }
    int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }
}
