import star.common.*;
import star.base.neo.*;
import star.motion.*;
import java.lang.reflect.*;
import java.util.*;

/** Probe #4 (reference-frame only): crack the MRF path. Output PROBE4>. */
public class probe_rf extends StarMacro {
    Simulation sim;
    public void execute() {
        sim = getActiveSimulation();
        p("start");
        // 1) getReferenceFrameManager called FIRST, typed, full stack on failure
        Object rfm = null;
        try {
            rfm = sim.getReferenceFrameManager();
            p("getReferenceFrameManager OK class=" + rfm.getClass().getName());
        } catch (Throwable t) {
            p("getReferenceFrameManager THREW " + t.getClass().getName() + ": " + t.getMessage());
            for (StackTraceElement e : t.getStackTrace()) { p("    at " + e); if (t.getStackTrace().length > 6) break; }
        }
        if (rfm != null) {
            dumpMethods("RFM", rfm, new String[]{"create", "Rotat", "Local", "get", "Reference"});
            // try several create signatures
            Object rf = null;
            for (String mname : new String[]{"createLocalReferenceFrame", "createReferenceFrame", "createRotatingReferenceFrame"}) {
                try {
                    rf = rfm.getClass().getMethod(mname, Class.class).invoke(rfm, RotatingReferenceFrame.class);
                    p(mname + "(Class) OK -> " + rf.getClass().getName()); break;
                } catch (Throwable t) { p(mname + "(Class) FAIL " + root(t)); }
                try {
                    rf = rfm.getClass().getMethod(mname).invoke(rfm);
                    p(mname + "() OK -> " + rf.getClass().getName()); break;
                } catch (Throwable t) { p(mname + "() FAIL " + root(t)); }
            }
            if (rf != null) {
                dumpMethods("RotRF", rf, new String[]{"set", "get", "Rotat", "Axis", "Rate", "Origin", "Coordinate", "Values"});
                dumpObjects("RotRF.getConditions", tryCall(rf, "getConditions"));
                dumpObjects("RotRF.getValues", tryCall(rf, "getValues"));
            }
        }
        // 2) brute-force manager class lookup
        for (String fqn : new String[]{
                "star.common.MotionManager", "star.motion.MotionManager", "star.common.ReferenceFrameManager",
                "star.common.LabReferenceFrameManager", "star.common.SimulationMotionManager"}) {
            try { Object o = sim.getClass().getMethod("get", Class.class).invoke(sim, Class.forName(fqn));
                p("sim.get(" + fqn + ") = " + (o == null ? "null" : o.getClass().getName())); }
            catch (Throwable t) { p("sim.get(" + fqn + ") FAIL " + root(t)); }
        }
        p("PROBE4_DONE");
    }
    void p(String s) { System.out.println("PROBE4> " + s); }
    String pres(Object o) { try { return (String) o.getClass().getMethod("getPresentationName").invoke(o); } catch (Throwable t) { return "?"; } }
    Object tryCall(Object o, String m) { if (o == null) return null; try { return o.getClass().getMethod(m).invoke(o); } catch (Throwable t) { return null; } }
    String root(Throwable t) { Throwable r = t; while (r.getCause() != null) r = r.getCause(); return r.getClass().getSimpleName() + ":" + r.getMessage(); }
    void dumpMethods(String label, Object o, String[] keys) {
        if (o == null) { p(label + " null"); return; }
        p("== " + label + " (" + o.getClass().getName() + ")");
        TreeSet<String> out = new TreeSet<>();
        for (Method mm : o.getClass().getMethods()) for (String k : keys) if (mm.getName().toLowerCase().contains(k.toLowerCase())) {
            StringBuilder sb = new StringBuilder(mm.getName()).append("(");
            Class<?>[] ps = mm.getParameterTypes();
            for (int i = 0; i < ps.length; i++) { if (i > 0) sb.append(","); sb.append(ps[i].getSimpleName()); }
            out.add(sb.append(")->").append(mm.getReturnType().getSimpleName()).toString()); break;
        }
        for (String s : out) p("   " + s);
    }
    void dumpObjects(String label, Object mgr) {
        if (mgr == null) { p(label + " null"); return; }
        try { Collection<?> objs = (Collection<?>) mgr.getClass().getMethod("getObjects").invoke(mgr);
            p("== " + label + " n=" + objs.size());
            for (Object o : objs) p("   " + o.getClass().getName() + " '" + pres(o) + "'");
        } catch (Throwable t) { p(label + " FAIL " + root(t)); }
    }
    public static void main(String[] a) { new probe_rf().execute(); }
}
