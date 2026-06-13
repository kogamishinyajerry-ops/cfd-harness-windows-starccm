import star.common.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeImportFile extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_import_file.log")); } catch (Throwable t) { return; }
        try {
            Object im = sim.getClass().getMethod("getImportManager").invoke(sim);
            pw.println("=== importFile variants ===");
            for (Method m : im.getClass().getMethods()) {
                if (m.getName().equals("importFile") || m.getName().equals("importFiles") || m.getName().equals("importParasolidTransmit") || m.getName().equals("importCaeFile") || m.getName().equals("importMeshFiles")) {
                    String ps = java.util.Arrays.toString(m.getParameterTypes());
                    pw.println("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
                }
            }
            // Also try direct import via GeometryPartManager
            pw.println("=== GPM.import* methods ===");
            Object gpm = sim.getClass().getMethod("getGeometryPartManager").invoke(sim);
            for (Method m : gpm.getClass().getMethods()) {
                if (m.getName().toLowerCase().contains("import") || m.getName().toLowerCase().contains("create") || m.getName().toLowerCase().contains("add")) {
                    String ps = java.util.Arrays.toString(m.getParameterTypes());
                    if (ps.length() < 100) pw.println("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
                }
            }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
