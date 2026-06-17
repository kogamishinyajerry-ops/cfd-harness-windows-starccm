import star.common.*;
import star.base.neo.*;
import java.lang.reflect.*;
import java.util.*;

/** Probe #3 (motion-only, no STL/mesh): resolve MRF setup -> MotionManager,
 *  RotatingMotion setters, and how a region's Motion Specification / Reference
 *  Frame is assigned. Output PROBE3>. */
public class probe_motion extends StarMacro {
    Simulation sim;
    public void execute() {
        sim = getActiveSimulation();
        p("start active=" + (sim != null));

        // empty region + minimal continuum so region values populate
        Region reg = null;
        try {
            reg = sim.getRegionManager().createEmptyRegion();
            ContinuumManager cm = sim.get(ContinuumManager.class);
            PhysicsContinuum cont = cm.createContinuum(PhysicsContinuum.class);
            for (String fqn : new String[]{"star.common.SteadyModel", "star.material.SingleComponentGasModel",
                    "star.coupledflow.CoupledFlowModel", "star.flow.IdealGasModel"})
                try { cont.enable(Class.forName(fqn)); } catch (Throwable t) {}
            cont.getClass().getMethod("add", Class.forName("star.common.Region")).invoke(cont, reg);
            p("region+continuum ready");
        } catch (Throwable t) { p("setup FAIL " + root(t)); }

        // all region method names (find conditions/values/motion accessors)
        try {
            TreeSet<String> names = new TreeSet<>();
            for (Method m : reg.getClass().getMethods())
                if (m.getParameterCount() == 0 && (m.getName().startsWith("get")))
                    names.add(m.getName() + "->" + m.getReturnType().getSimpleName());
            p("== Region zero-arg getters:");
            for (String s : names) p("   " + s);
        } catch (Throwable t) { p("region getters FAIL " + root(t)); }

        // MotionManager
        Object mm = simGet("star.common.MotionManager");
        dumpMethods("MotionManager", mm, new String[]{"create", "Motion", "get"});
        Object rot = null;
        if (mm != null) {
            for (String cand : new String[]{"star.motion.RotatingMotion"}) {
                try {
                    rot = mm.getClass().getMethod("createMotion", Class.class).invoke(mm, Class.forName(cand));
                    p("created motion=" + rot.getClass().getName());
                } catch (Throwable t) { p("createMotion FAIL " + root(t)); }
            }
        }
        if (rot != null) dumpMethods("RotatingMotion", rot, new String[]{"Rotat", "Axis", "Rate", "Origin", "Coordinate", "Direction", "getValues", "get"});

        // region conditions/values after motion exists
        dumpObjects("Region.getConditions", tryCall(reg, "getConditions"));
        dumpObjects("Region.getValues", tryCall(reg, "getValues"));
        // dump MotionSpecification class methods if present
        try {
            Object rc = tryCall(reg, "getValues");
            Collection<?> objs = (Collection<?>) rc.getClass().getMethod("getObjects").invoke(rc);
            for (Object o : objs) {
                String cn = o.getClass().getName();
                if (cn.toLowerCase().contains("motion") || cn.toLowerCase().contains("frame"))
                    dumpMethods("RegionValue " + cn, o, new String[]{"set", "Motion", "Frame", "Reference"});
            }
            Object cc = tryCall(reg, "getConditions");
            objs = (Collection<?>) cc.getClass().getMethod("getObjects").invoke(cc);
            for (Object o : objs) {
                String cn = o.getClass().getName();
                if (cn.toLowerCase().contains("motion") || cn.toLowerCase().contains("frame"))
                    dumpMethods("RegionCond " + cn, o, new String[]{"set", "Option", "Motion", "Frame"});
            }
        } catch (Throwable t) { p("motionspec dump FAIL " + root(t)); }

        p("PROBE3_DONE");
    }
    void p(String s) { System.out.println("PROBE3> " + s); }
    String pres(Object o) { try { return (String) o.getClass().getMethod("getPresentationName").invoke(o); } catch (Throwable t) { return "?"; } }
    Object simGet(String... f) { for (String x : f) { try { return sim.getClass().getMethod("get", Class.class).invoke(sim, Class.forName(x)); } catch (Throwable t) {} } return null; }
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
    public static void main(String[] a) { new probe_motion().execute(); }
}
