import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeSimGet extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_sim_get.log")); } catch (Throwable t) { return; }
        try {
            Class<?> sc = sim.getClass();
            pw.println("=== Simulation methods named getImport* or *Manager ===");
            for (Method m : sc.getMethods()) {
                String n = m.getName();
                if (n.toLowerCase().contains("import") || n.toLowerCase().contains("manager")) {
                    String ps = java.util.Arrays.toString(m.getParameterTypes());
                    if (ps.length() < 100) pw.println("  " + n + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
                }
            }
            // Also try RootObject.get for the specific class
            pw.println("=== Test sim.get(ImportManager.class) ===");
            try {
                Class<?> im = Class.forName("star.common.ImportManager");
                Object r = sc.getMethod("get", Class.class).invoke(sim, im);
                pw.println("  result: " + r);
            } catch (Throwable t) { pw.println("  FAIL: " + t); }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
