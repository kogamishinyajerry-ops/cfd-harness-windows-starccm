// Probe9.java — DEC-005 attempt 1/2
// Enumerate region.getRepresentation().getInternalMesh() methods and try
// to dump per-cell-center field values via any reflective path. The
// existing 1-cell-region SumReport path is dead (createSimpleBlockPart
// does not exist on RegionManager per the LDC_STATUS.md and the
// step9 log). The new path is: walk the InternalMesh directly to get
// cell centers, then find a way to read the field value at each center
// (InternalMesh.getValueAt / InternalMesh.getCellValue / similar).
//
// Output: a CSV at "D:\CFD-harness-Windows-StarCCM\probe9_internal_mesh_diag.log"
// summarizing the method enum, the cell-center array shape, and any
// viable value path.
import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class Probe9 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        sim.println("=== Probe9 START ===");
        PrintWriter pw = null;
        try {
            pw = new PrintWriter(new FileWriter(
                "D:\\CFD-harness-Windows-StarCCM\\probe9_internal_mesh_diag.log"));
        } catch (Throwable t) {
            sim.println("can't open log: " + t);
            return;
        }
        try {
            // Locate the cavity region
            RegionManager rm = sim.getRegionManager();
            Region reg = null;
            for (Object r : rm.getRegions()) {
                if (r instanceof Region) { reg = (Region) r; break; }
            }
            if (reg == null) { pw.println("no region"); pw.close(); return; }
            pw.println("region: " + reg.getPresentationName() + " class=" + reg.getClass().getName());
            sim.println("region: " + reg.getPresentationName());

            // Get representation
            Object rep = null;
            for (String gn : new String[]{"getRepresentation", "getMeshRepresentation", "getMeshManager", "getMesh"}) {
                try {
                    Method m = reg.getClass().getMethod(gn);
                    Object o = m.invoke(reg);
                    if (o != null) { rep = o; pw.println("region." + gn + " -> " + o.getClass().getName()); sim.println("region." + gn + " -> " + o.getClass().getName()); break; }
                } catch (NoSuchMethodException nsme) {}
                catch (Throwable t) { pw.println("region." + gn + " err: " + t); }
            }
            if (rep == null) { pw.println("no representation"); pw.close(); return; }

            // Get internal mesh
            Object im = null;
            for (String gn : new String[]{"getInternalMesh", "getMesh", "getVolumeMesh", "getMeshObject"}) {
                try {
                    Method m = rep.getClass().getMethod(gn);
                    Object o = m.invoke(rep);
                    if (o != null) { im = o; pw.println("rep." + gn + " -> " + o.getClass().getName()); sim.println("rep." + gn + " -> " + o.getClass().getName()); break; }
                } catch (NoSuchMethodException nsme) {}
                catch (Throwable t) { pw.println("rep." + gn + " err: " + t); }
            }
            if (im == null) { pw.println("no internal mesh"); pw.close(); return; }

            // Enumerate InternalMesh methods
            pw.println("--- InternalMesh class: " + im.getClass().getName() + " ---");
            pw.println("--- ALL methods ---");
            int n = 0;
            for (Method m : im.getClass().getMethods()) {
                String name = m.getName();
                Class<?>[] pts = m.getParameterTypes();
                StringBuilder sb = new StringBuilder("  ");
                sb.append(name).append("(");
                for (int i = 0; i < pts.length; i++) {
                    if (i > 0) sb.append(", ");
                    sb.append(pts[i].getSimpleName());
                }
                sb.append(") -> ").append(m.getReturnType().getSimpleName());
                if (sb.length() < 140) { pw.println(sb.toString()); n++; }
            }
            pw.println("(" + n + " methods)");

            // Also walk superclass methods
            pw.println("--- superclass chain ---");
            for (Class<?> c = im.getClass().getSuperclass(); c != null && c != Object.class; c = c.getSuperclass()) {
                pw.println("  super: " + c.getName());
                for (Method m : c.getDeclaredMethods()) {
                    String name = m.getName();
                    if (name.contains("ell") || name.contains("oord") || name.contains("alue") || name.contains("ertex") || name.contains("ode")) {
                        StringBuilder sb = new StringBuilder("    ");
                        sb.append(name).append("(");
                        Class<?>[] pts = m.getParameterTypes();
                        for (int i = 0; i < pts.length; i++) {
                            if (i > 0) sb.append(", ");
                            sb.append(pts[i].getSimpleName());
                        }
                        sb.append(") -> ").append(m.getReturnType().getSimpleName());
                        if (sb.length() < 140) pw.println(sb.toString());
                    }
                }
            }

            // Try getCellCenters
            Object cc = null;
            for (String mn : new String[]{"getCellCenters", "getCellCentroids", "getCenters"}) {
                try {
                    Method m = im.getClass().getMethod(mn);
                    cc = m.invoke(im);
                    if (cc != null) {
                        pw.println("getCellCenters via " + mn + " -> " + cc.getClass().getName());
                        if (cc instanceof double[]) pw.println("  len=" + ((double[])cc).length);
                        else if (cc instanceof float[]) pw.println("  len=" + ((float[])cc).length);
                        else if (cc instanceof Object[]) pw.println("  arr.length=" + ((Object[])cc).length);
                        break;
                    }
                } catch (NoSuchMethodException nsme) {}
                catch (Throwable t) { pw.println(mn + " err: " + t); }
            }

            // Try getValues0 / getXValues / getYValues / getZValues
            pw.println("--- coord arrays ---");
            for (String mn : new String[]{"getValues0", "getXValues", "getYValues", "getZValues", "getNodeCoordinates", "getNodeX", "getNodeY"}) {
                try {
                    Method m = im.getClass().getMethod(mn);
                    Object o = m.invoke(im);
                    if (o == null) continue;
                    if (o instanceof double[]) pw.println(mn + " -> double[len=" + ((double[])o).length + "]");
                    else if (o instanceof float[]) pw.println(mn + " -> float[len=" + ((float[])o).length + "]");
                    else if (o instanceof int[]) pw.println(mn + " -> int[len=" + ((int[])o).length + "]");
                    else pw.println(mn + " -> " + o.getClass().getName());
                } catch (NoSuchMethodException nsme) {}
                catch (Throwable t) { pw.println(mn + " err: " + t); }
            }

            // Try getValueAt / getValue / getCellValue
            pw.println("--- value methods (any-arg) ---");
            for (Method m : im.getClass().getMethods()) {
                String name = m.getName();
                if (name.startsWith("getValue") || name.startsWith("getCellValue") || name.contains("Sample") || name.contains("Probe") || name.contains("SampleAt")) {
                    StringBuilder sb = new StringBuilder("  ");
                    sb.append(name).append("(");
                    Class<?>[] pts = m.getParameterTypes();
                    for (int i = 0; i < pts.length; i++) {
                        if (i > 0) sb.append(", ");
                        sb.append(pts[i].getName());
                    }
                    sb.append(") -> ").append(m.getReturnType().getName());
                    if (sb.length() < 140) pw.println(sb.toString());
                }
            }

            // Try InternalMesh.assessFf / getInternalValue / similar
            // (try names)
            for (String mn : new String[]{"assessFf", "getInternalValue", "getFieldFunctionValue", "extractValue", "evaluate"}) {
                try {
                    Method m = im.getClass().getMethod(mn);
                    pw.println("FOUND: " + mn + "() -> " + m.getReturnType().getName());
                } catch (NoSuchMethodException nsme) {}
            }

        } catch (Throwable t) {
            pw.println("FATAL: " + t);
        }
        pw.close();
        sim.println("=== Probe9 END ===");
    }
}
