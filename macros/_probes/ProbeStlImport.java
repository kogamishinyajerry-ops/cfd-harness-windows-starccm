import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeStlImport extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_stl_import.log")); } catch (Throwable t) { return; }
        try {
            // Try SurfaceMeshLoader
            for (String cn : new String[]{"star.surface.SurfaceMeshLoader", "star.surface.MeshImporter",
                "star.surface.STLImporter", "star.common.SurfaceMeshLoader",
                "star.surface.STLLoader", "star.surface.SurfaceMeshImporter",
                "star.surface.SurfaceMesh", "star.common.SurfaceMeshPartManager",
                "star.surfacemesh.SurfaceMeshLoader", "star.surfacemesh.SurfaceMeshImporter",
                "star.cad.SurfaceMeshImporter", "star.geom.SurfaceMeshImporter"}) {
                try {
                    Class<?> c = Class.forName(cn);
                    pw.println("FOUND: " + cn);
                    for (Method m : c.getMethods()) {
                        if (m.getName().toLowerCase().contains("import") || m.getName().toLowerCase().contains("load") || m.getName().toLowerCase().contains("create") || m.getName().toLowerCase().contains("execute")) {
                            String ps = java.util.Arrays.toString(m.getParameterTypes());
                            if (ps.length() < 90) pw.println("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
                        }
                    }
                } catch (ClassNotFoundException cnf) { pw.println("-- " + cn); }
            }
            // Also probe GeometryPartManager.createPart or similar
            pw.println("=== GPM creation methods ===");
            Object gpm = sim.getClass().getMethod("getGeometryPartManager").invoke(sim);
            for (Method m : gpm.getClass().getMethods()) {
                if (m.getName().toLowerCase().contains("create") || m.getName().toLowerCase().contains("import")) {
                    String ps = java.util.Arrays.toString(m.getParameterTypes());
                    if (ps.length() < 90) pw.println("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
                }
            }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
