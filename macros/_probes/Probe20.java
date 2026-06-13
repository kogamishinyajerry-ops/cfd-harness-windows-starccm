import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe20 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe20_probe_objs.log")); } catch (Throwable t) { return; }
        try {
            pw.println("=== probe for Probe / PointProbe classes ===");
            String[] probeClasses = {
                "star.common.Probe", "star.common.PointProbe", "star.common.LineProbe",
                "star.common.SampleProbe", "star.common.FieldSample",
                "star.common.ProbeManager", "star.common.PointProbeManager",
                "star.common.ProbeGroup", "star.common.ProbePlot"
            };
            for (String cn : probeClasses) {
                try { Class.forName(cn); pw.println("  RESOLVED: " + cn); } catch (ClassNotFoundException cnf) { pw.println("  NOT FOUND: " + cn); }
            }
            // Try getProbeManager / getProbes on Simulation
            pw.println("=== Simulation getProbe* methods ===");
            for (Method m : sim.getClass().getMethods()) {
                if (m.getName().toLowerCase().contains("probe")) {
                    StringBuilder sb = new StringBuilder("  ");
                    sb.append(m.getName()).append("(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sb.append(", ");
                        sb.append(pts[i].getSimpleName());
                    }
                    sb.append(") -> ").append(m.getReturnType().getSimpleName());
                    if (sb.length() < 130) pw.println(sb.toString());
                }
            }
            // Try sim.get(Class) for ProbeManager
            try {
                Class pmCls = Class.forName("star.common.ProbeManager");
                Object pm = sim.get(pmCls);
                pw.println("sim.get(ProbeManager) -> " + (pm == null ? "null" : pm.getClass().getName()));
            } catch (ClassNotFoundException cnf) { pw.println("ProbeManager not in classpath"); }
            // FieldFunctionManager createProbe
            try {
                FieldFunctionManager ffm = sim.getFieldFunctionManager();
                for (Method m : ffm.getClass().getMethods()) {
                    if (m.getName().toLowerCase().contains("probe") || m.getName().toLowerCase().contains("sample")) {
                        StringBuilder sb = new StringBuilder("  ffm.");
                        sb.append(m.getName()).append("(");
                        Class<?>[] pts = m.getParameterTypes();
                        for (int i = 0; i < pts.length; i++) {
                            if (i > 0) sb.append(", ");
                            sb.append(pts[i].getSimpleName());
                        }
                        sb.append(") -> ").append(m.getReturnType().getSimpleName());
                        if (sb.length() < 130) pw.println(sb.toString());
                    }
                }
            } catch (Throwable t) { pw.println("ffm probe walk: " + t); }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
