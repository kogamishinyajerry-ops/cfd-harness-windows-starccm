import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbePartRegion extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\CFD-harness-Windows-StarCCM\\probe_part_region.log")); } catch (Throwable t) { return; }
        try {
            RegionManager rm = sim.getRegionManager();
            pw.println("=== Regions: " + rm.getRegions().size() + " ===");
            int idx = 0;
            for (Region r : rm.getRegions()) {
                pw.println("  Region " + idx + " : " + r.getPresentationName() + " (" + r.getClass().getSimpleName() + ")");
                idx++;
            }
            try {
                Object pm = sim.getClass().getMethod("getPartManager").invoke(sim);
                Method gps = pm.getClass().getMethod("getParts");
                java.util.List ps = (java.util.List) gps.invoke(pm);
                pw.println("=== Parts (PartManager): " + ps.size() + " ===");
                for (Object p : ps) {
                    Method pn = p.getClass().getMethod("getPresentationName");
                    pw.println("  Part: " + pn.invoke(p) + " (" + p.getClass().getSimpleName() + ")");
                }
            } catch (Throwable t) { pw.println("PartManager probe FAIL: " + t); }
            try {
                Object gpm = sim.getClass().getMethod("getGeometryPartManager").invoke(sim);
                pw.println("=== GPM class: " + gpm.getClass().getName() + " ===");
                Method gpGet = gpm.getClass().getMethod("getParts");
                java.util.List gps = (java.util.List) gpGet.invoke(gpm);
                pw.println("=== GPM parts: " + gps.size() + " ===");
                for (Object gp : gps) {
                    pw.println("  GP: " + gp.getClass().getSimpleName() + " pres=" + gp.getClass().getMethod("getPresentationName").invoke(gp));
                }
            } catch (Throwable t) { pw.println("GPM probe FAIL: " + t); }
            try {
                Object imm = sim.getClass().getMethod("getImportedModelManager").invoke(sim);
                Method ig = imm.getClass().getMethod("getImportedModels");
                java.util.List ims = (java.util.List) ig.invoke(imm);
                pw.println("=== Imported models: " + ims.size() + " ===");
                for (Object im : ims) {
                    pw.println("  " + im.getClass().getSimpleName() + " pres=" + im.getClass().getMethod("getPresentationName").invoke(im));
                }
            } catch (Throwable t) { pw.println("IMM probe FAIL: " + t); }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
