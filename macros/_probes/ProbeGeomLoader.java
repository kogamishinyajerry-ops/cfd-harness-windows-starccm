import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeGeomLoader extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_geom_loader.log")); } catch (Throwable t) { return; }
        try {
            // Look for GeometryPartManager
            try {
                Class<?> gpm = Class.forName("star.geom.GeometryPartManager");
                pw.println("=== star.geom.GeometryPartManager found ===");
                for (Method m : gpm.getMethods()) {
                    if (m.getName().toLowerCase().contains("import") || m.getName().toLowerCase().contains("load") || m.getName().toLowerCase().contains("create")) {
                        pw.println("  " + m.getName() + "(" + java.util.Arrays.toString(m.getParameterTypes()) + ") -> " + m.getReturnType().getSimpleName());
                    }
                }
            } catch (ClassNotFoundException cnf) { pw.println("star.geom.GeometryPartManager NOT FOUND"); }
            // Try to find any class in 'star' package with "Loader" in name
            // We can't enumerate packages, so try common ones
            String[] tryClasses = {
                "star.surface.MeshImporter", "star.surface.SurfaceMeshImporter",
                "star.surface.STLImporter", "star.surface.STLLoader",
                "star.cadmodel.CadImporter", "star.common.GeometryPartManager",
                "star.geom.GeometryPartManager", "star.common.STLLoader",
                "star.surfprep.SurfaceMesh", "star.meshing.MeshImporter",
                "star.common.Importer", "star.common.CADImporter",
                "star.surface.SurfaceMeshLoader", "star.surface.MeshLoader"
            };
            pw.println("=== Class probe ===");
            for (String cn : tryClasses) {
                try {
                    Class<?> c = Class.forName(cn);
                    pw.println("FOUND: " + cn);
                    for (Method m : c.getMethods()) {
                        if (m.getName().toLowerCase().contains("set") || m.getName().toLowerCase().contains("import")
                            || m.getName().toLowerCase().contains("load") || m.getName().toLowerCase().contains("execute")) {
                            String ps = java.util.Arrays.toString(m.getParameterTypes());
                            if (ps.length() < 80) pw.println("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
                        }
                    }
                } catch (ClassNotFoundException cnf) {
                    pw.println("  -- " + cn);
                }
            }
            // Enumerate all star.* classes via packages? Not possible without Class.forName.
            // Alternative: try ImportManager
            try {
                Class<?> im = Class.forName("star.common.ImportManager");
                pw.println("=== star.common.ImportManager found ===");
                for (Method m : im.getMethods()) {
                    if (m.getName().toLowerCase().contains("import") || m.getName().toLowerCase().contains("create")
                        || m.getName().toLowerCase().contains("load") || m.getName().toLowerCase().contains("get")) {
                        String ps = java.util.Arrays.toString(m.getParameterTypes());
                        if (ps.length() < 80) pw.println("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
                    }
                }
            } catch (ClassNotFoundException cnf) { pw.println("star.common.ImportManager NOT FOUND"); }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
