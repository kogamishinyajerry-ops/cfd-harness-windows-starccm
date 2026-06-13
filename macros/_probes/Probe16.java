// Probe16.java — DEC-005 attempt 8/8
// Position FF is a vector. Get its components Position[0], Position[1], Position[2]
// (or getComponentFunction(0/1/2)) and try splitRegionsByFunction with the Y component.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe16 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe16 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe16_position_components.log"));
        } catch (Throwable t) { sim.println("can't open log: " + t); return; }
        try {
            FieldFunctionManager ffm = sim.getFieldFunctionManager();
            Object mm = sim.getMeshManager();
            RegionManager rm = sim.getRegionManager();
            Region reg = null;
            for (Object r : rm.getRegions()) { if (r instanceof Region) { reg = (Region) r; break; } }
            FieldFunction velFF = ffm.getFunction("Velocity");
            FieldFunction posFF = ffm.getFunction("Position");
            pw.println("posFF: " + posFF.getClass().getName());

            // Get each component
            for (int i = 0; i < 3; i++) {
                FieldFunction comp = posFF.getComponentFunction(i);
                pw.println("posFF[" + i + "]: " + comp.getClass().getName() + " pres=" + comp.getPresentationName());
                try {
                    Object n = mm.getClass().getMethod("previewSplitRegions", FieldFunction.class, Collection.class)
                        .invoke(mm, comp, java.util.Collections.singletonList(reg));
                    pw.println("  previewSplitRegions(posFF[" + i + "]) -> " + n);
                } catch (Throwable t) { pw.println("  previewSplitRegions(posFF[" + i + "]) FAIL: " + t.getMessage()); }
                try {
                    Object n = mm.getClass().getMethod("previewSplitRegions", FieldFunction.class, Collection.class, NeoProperty.class)
                        .invoke(mm, comp, java.util.Collections.singletonList(reg), new NeoProperty());
                    pw.println("  previewSplitRegions(posFF[" + i + "], props) -> " + n);
                } catch (NoSuchMethodException nsme) { /* skip */ }
            }

            // Now try the actual splitRegionsByFunction with Position[1] (Y component)
            FieldFunction posY = posFF.getComponentFunction(1);
            pw.println("=== ACTUAL splitRegionsByFunction(Position[1]) ===");
            try {
                // First preview to see how many regions
                int nSplits = (Integer) mm.getClass().getMethod("previewSplitRegions", FieldFunction.class, Collection.class)
                    .invoke(mm, posY, java.util.Collections.singletonList(reg));
                pw.println("  preview returns: " + nSplits);
            } catch (Throwable t) { pw.println("  preview FAIL: " + t); }

            // Try the actual split. Use a threshold via NeoProperty? 
            // STAR-CCM+ splitRegionsByFunction splits at iso-contour bands.
            // For y_FF, splitting at y=0.5 (midpoint) would give 2 regions.
            // We need 17 thresholds for 17 slabs. But splitRegionsByFunction(FF, regions)
            // splits based on internal logic, not user thresholds.
            // 
            // Test: just split with posY and see how many regions result
            try {
                int before = rm.getRegions().size();
                pw.println("  regions before split: " + before);
                mm.getClass().getMethod("splitRegionsByFunction", FieldFunction.class, Collection.class)
                    .invoke(mm, posY, java.util.Collections.singletonList(reg));
                int after = rm.getRegions().size();
                pw.println("  regions after split: " + after);
                // Get all new regions and their extents
                java.util.List<Object> newRegions = new java.util.ArrayList<>();
                for (Object r : rm.getRegions()) newRegions.add(r);
                for (Object r : newRegions) {
                    if (r instanceof Region) {
                        double[] ext = (double[]) mm.getClass().getMethod("getRegionExtents", Region.class).invoke(mm, (Region) r);
                        pw.println("    region extents: " + (ext == null ? "null" : java.util.Arrays.toString(ext)));
                    }
                }
            } catch (Throwable t) { pw.println("  splitRegionsByFunction FAIL: " + t); }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe16 END ===");
    }
}
