import star.common.*;
import star.base.neo.*;
import java.lang.reflect.*;
import java.util.*;

/** Probe #7: dump ALL sim children and ALL SimulationTools children (unfiltered)
 *  with class + name, to locate the reference-frame / motion manager. Output PROBE7>. */
public class probe_children extends StarMacro {
    Simulation sim;
    public void execute() {
        sim = getActiveSimulation();
        p("start");
        dumpChildren("SIM", sim);
        try {
            Object tools = null;
            for (Object o : (Collection<?>) sim.getClass().getMethod("getChildren").invoke(sim))
                if (o.getClass().getName().equals("star.common.SimulationTools")) { tools = o; break; }
            if (tools != null) {
                dumpChildren("TOOLS", tools);
                // try getClientServerObject by likely names
                for (String nm : new String[]{"Reference Frames", "Motions", "Reference Frame", "Motion",
                        "ReferenceFrameManager", "MotionManager", "Coordinate Systems"}) {
                    try { Object o = tools.getClass().getMethod("getClientServerObject", String.class).invoke(tools, nm);
                        p("tools.getCSO('" + nm + "') = " + (o == null ? "null" : o.getClass().getName())); }
                    catch (Throwable t) { p("tools.getCSO('" + nm + "') FAIL " + root(t)); }
                }
            }
        } catch (Throwable t) { p("tools FAIL " + root(t)); }
        p("PROBE7_DONE");
    }
    void dumpChildren(String label, Object o) {
        try {
            Collection<?> ch = (Collection<?>) o.getClass().getMethod("getChildren").invoke(o);
            p("== " + label + " children n=" + ch.size());
            for (Object c : ch) p("   " + c.getClass().getName() + " '" + pres(c) + "'");
        } catch (Throwable t) { p(label + " getChildren FAIL " + root(t)); }
    }
    void p(String s) { System.out.println("PROBE7> " + s); }
    String pres(Object o) { try { return (String) o.getClass().getMethod("getPresentationName").invoke(o); } catch (Throwable t) { return "?"; } }
    String root(Throwable t) { Throwable r = t; while (r.getCause() != null) r = r.getCause(); return r.getClass().getSimpleName() + ":" + r.getMessage(); }
    public static void main(String[] a) { new probe_children().execute(); }
}
