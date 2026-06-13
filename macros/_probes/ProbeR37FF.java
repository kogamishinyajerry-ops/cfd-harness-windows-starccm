import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeR37FF extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_r37_ff.log")); } catch (Throwable t) { return; }
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            // Dump the full pool
            try {
                Object all = ffm.getClass().getMethod("getObjects").invoke(ffm);
                if (all instanceof Collection) {
                    pw.println("=== FFM pool size: " + ((Collection<?>) all).size() + " ===");
                    for (Object f : (Collection<?>) all) {
                        if (f instanceof FieldFunction) {
                            String n = ((FieldFunction) f).getPresentationName();
                            String cn = f.getClass().getSimpleName();
                            if (n != null && !n.startsWith("<") && (n.toLowerCase().contains("mach") || n.toLowerCase().contains("mass") || n.toLowerCase().contains("flow") || n.toLowerCase().contains("pressure") || n.toLowerCase().contains("velocity"))) {
                                pw.println("  " + n + " (" + cn + ")");
                            }
                        }
                    }
                }
            } catch (Throwable t) { pw.println("pool dump FAIL: " + t); }
            // Try specific names
            String[] tryF = {"Mach", "MachNumber", "SupersonicMach", "StaticMach", "M", "", "Mach Index"};
            for (String n : tryF) {
                try {
                    FieldFunction f = ffm.getFunction(n);
                    String cn = f.getClass().getSimpleName();
                    String pn = f.getPresentationName();
                    pw.println("  " + n + " -> " + cn + " pres=" + pn);
                } catch (Throwable t) { pw.println("  " + n + " FAIL: " + t.getMessage()); }
            }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
