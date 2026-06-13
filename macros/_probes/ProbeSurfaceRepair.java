import star.common.*;
import star.base.neo.*;
//
import star.surface.*;
import star.meshing.*;
//
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeSurfaceRepair extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_surface_repair.log")); } catch (Throwable t) { return; }
        try {
            // Get ImportedSurfaceManager
            pw.println("=== Surface management classes probe ===");
            String[] classNames = {
                "star.surface.ImportedSurfaceManager",
                "star.surface.ImportedSurface",
                "star.surface.SurfaceRepairOperation",
                "star.surface.SurfaceRepairManager",
                "star.surfprep.SurfaceMesh",
                "star.surface.SurfaceImporter",
                "star.surface.SurfaceManager",
                "star.cad.SurfaceRepair",
                "star.cadmodel.SurfaceRepairOperation",
                "star.common.ImportedSurface",
                "star.common.ImportedSurfaceManager"
            };
            for (String cn : classNames) {
                try {
                    Class<?> c = Class.forName(cn);
                    pw.println("FOUND: " + cn);
                    for (Method m : c.getMethods()) {
                        if (m.getName().toLowerCase().contains("repair") || m.getName().toLowerCase().contains("createpart") || m.getName().toLowerCase().contains("createregion") || m.getName().toLowerCase().contains("convert")) {
                            String ps = java.util.Arrays.toString(m.getParameterTypes());
                            if (ps.length() < 100) pw.println("  " + m.getName() + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
                        }
                    }
                } catch (ClassNotFoundException cnf) {
                    pw.println("-- " + cn);
                }
            }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
