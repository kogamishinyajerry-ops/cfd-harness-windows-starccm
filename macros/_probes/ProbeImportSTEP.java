import star.common.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeImportSTEP extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_import_step.log")); } catch (Throwable t) { return; }
        try {
            Object im = sim.getClass().getMethod("getImportManager").invoke(sim);
            // Import the STEP file
            String stepPath = "D:\\\\CFD-harness-Windows-StarCCM\\\\scripts\\\\rotor37_extruded.step";
            pw.println("=== Importing STEP: " + stepPath + " ===");
            try {
                Method importCae = im.getClass().getMethod("importCaeFile", String.class, Class.forName("star.common.Units"), boolean.class);
                // We need Units - try with no units
                importCae.invoke(im, stepPath, null, true);
                pw.println("importCaeFile OK (no units)");
            } catch (Throwable t) {
                pw.println("importCaeFile FAIL: " + t);
                // Try importFiles
                try {
                    java.util.List lst = new java.util.ArrayList();
                    lst.add(stepPath);
                    Method importFiles = im.getClass().getMethod("importFiles", java.util.List.class);
                    importFiles.invoke(im, lst);
                    pw.println("importFiles OK");
                } catch (Throwable t2) {
                    pw.println("importFiles FAIL: " + t2);
                }
            }
            // Check parts after import
            Object gpm = sim.getClass().getMethod("getGeometryPartManager").invoke(sim);
            Method gpGet = gpm.getClass().getMethod("getParts");
            java.util.List gps = (java.util.List) gpGet.invoke(gpm);
            pw.println("=== After import: GPM parts = " + gps.size() + " ===");
            for (Object gp : gps) {
                Method pn = gp.getClass().getMethod("getPresentationName");
                String name = (String) pn.invoke(gp);
                pw.println("  GP: " + gp.getClass().getSimpleName() + " pres=" + name);
            }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
