import star.common.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbePartsV7 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_parts_v7.log")); } catch (Throwable t) { return; }
        try {
            Object gpm = sim.getClass().getMethod("getGeometryPartManager").invoke(sim);
            Method gpGet = gpm.getClass().getMethod("getParts");
            java.util.List gps = (java.util.List) gpGet.invoke(gpm);
            pw.println("=== GPM parts: " + gps.size() + " ===");
            for (Object gp : gps) {
                Method pn = gp.getClass().getMethod("getPresentationName");
                String name = (String) pn.invoke(gp);
                pw.println("  GP: " + gp.getClass().getSimpleName() + " pres=" + name);
                // Try getPartBodies
                try {
                    Method gb = gp.getClass().getMethod("getPartBodies");
                    java.util.List bodies = (java.util.List) gb.invoke(gp);
                    pw.println("    bodies: " + bodies.size());
                } catch (Throwable t) { pw.println("    no getPartBodies"); }
                // Try getPartSurfaces
                try {
                    Method gs = gp.getClass().getMethod("getPartSurfaces");
                    java.util.List surfs = (java.util.List) gs.invoke(gp);
                    pw.println("    surfaces: " + surfs.size());
                    for (Object s : surfs) {
                        Method spn = s.getClass().getMethod("getPresentationName");
                        pw.println("      surface: " + spn.invoke(s));
                    }
                } catch (Throwable t) { pw.println("    no getPartSurfaces"); }
            }
            RegionManager rm = sim.getRegionManager();
            pw.println("=== Regions: " + rm.getRegions().size() + " ===");
            int idx = 0;
            for (Region r : rm.getRegions()) {
                pw.println("  Region " + idx + " : " + r.getPresentationName());
                idx++;
            }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
