import star.common.*;
import star.base.neo.*;
import java.lang.reflect.*;
import java.util.*;

/** Probe #5: enumerate sim child managers to locate the concrete reference-frame /
 *  motion manager, and inspect the lab coordinate system route. Output PROBE5>. */
public class probe_tree extends StarMacro {
    Simulation sim;
    public void execute() {
        sim = getActiveSimulation();
        p("start");
        // make a region+continuum first in case managers are lazy
        try {
            Region reg = sim.getRegionManager().createEmptyRegion();
            ContinuumManager cm = sim.get(ContinuumManager.class);
            PhysicsContinuum cont = cm.createContinuum(PhysicsContinuum.class);
            for (String f : new String[]{"star.common.SteadyModel","star.material.SingleComponentGasModel",
                    "star.coupledflow.CoupledFlowModel","star.flow.IdealGasModel"})
                try { cont.enable(Class.forName(f)); } catch (Throwable t) {}
            cont.getClass().getMethod("add", Class.forName("star.common.Region")).invoke(cont, reg);
        } catch (Throwable t) { p("setup " + root(t)); }

        // enumerate sim children: class + name, flag motion/frame/reference/coordinate
        try {
            Collection<?> ch = (Collection<?>) sim.getClass().getMethod("getChildren").invoke(sim);
            p("sim children n=" + ch.size());
            for (Object o : ch) {
                String cn = o.getClass().getName();
                String low = cn.toLowerCase();
                boolean flag = low.contains("motion") || low.contains("frame") || low.contains("reference") || low.contains("coordinate") || low.contains("tool");
                if (flag) p("  *CHILD " + cn + " '" + pres(o) + "'");
            }
            p("  (non-flagged children omitted)");
        } catch (Throwable t) { p("children FAIL " + root(t)); }

        // coordinate system manager -> lab CSYS -> local frames?
        try {
            Object csm = sim.getCoordinateSystemManager();
            p("CSM=" + csm.getClass().getName());
            dumpMethods("CSM", csm, new String[]{"Lab", "Local", "Reference", "create", "Rotat", "getLab"});
            Object lab = tryCall(csm, "getLabCoordinateSystem");
            if (lab != null) {
                p("lab=" + lab.getClass().getName());
                dumpMethods("Lab", lab, new String[]{"Local", "Reference", "Rotat", "create", "getLocal"});
                Object lcm = tryCall(lab, "getLocalCoordinateSystemManager");
                if (lcm != null) dumpMethods("LocalCSM", lcm, new String[]{"create"});
            }
        } catch (Throwable t) { p("CSM FAIL " + root(t)); }

        // also: dump sim methods returning *Manager with Motion/Frame/Reference (full names)
        try {
            p("== sim getters returning managers (Motion/Frame/Reference/Tool):");
            TreeSet<String> out = new TreeSet<>();
            for (Method m : sim.getClass().getMethods()) {
                if (m.getParameterCount() != 0) continue;
                String rn = m.getReturnType().getSimpleName().toLowerCase();
                String mn = m.getName().toLowerCase();
                if (rn.contains("manager") && (mn.contains("motion") || mn.contains("frame") || mn.contains("reference") || mn.contains("tool")))
                    out.add(m.getName() + "->" + m.getReturnType().getName());
            }
            for (String s : out) p("   " + s);
        } catch (Throwable t) {}

        p("PROBE5_DONE");
    }
    void p(String s) { System.out.println("PROBE5> " + s); }
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
    public static void main(String[] a) { new probe_tree().execute(); }
}
