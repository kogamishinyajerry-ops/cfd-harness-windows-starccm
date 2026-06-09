import star.common.*;
import java.lang.reflect.*;
public class ProbeFindPM extends StarMacro {
  public void execute() {
    Simulation sim = getActiveSimulation();
    sim.println("=== ProbeFindPM ===");
    for (String cn : new String[]{
        "star.common.ProbeManager","star.probes.ProbeManager","star.common.probes.ProbeManager",
        "star.probes.PointProbe","star.common.PointProbe"}) {
      try { Class c = Class.forName(cn); sim.println("OK: " + cn + " -> " + c.getName()); }
      catch (Throwable t) { sim.println("FAIL: " + cn); }
    }
    // getMethod on sim
    for (String mn : new String[]{"getProbeManager","getPointProbes","getProbes"}) {
      try {
        Method m = Simulation.class.getMethod(mn, new Class[0]);
        Object o = m.invoke(sim, new Object[0]);
        sim.println("sim." + mn + "() -> " + (o==null?"null":o.getClass().getName()));
      } catch (Throwable t) { sim.println("sim." + mn + " FAIL: " + t.getClass().getSimpleName()); }
    }
    sim.println("=== DONE ===");
  }
}
