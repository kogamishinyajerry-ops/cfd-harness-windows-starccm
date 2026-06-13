import star.common.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeImportSTEP2 extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_import_step2.log")); } catch (Throwable t) { return; }
        try {
            Object im = sim.getClass().getMethod("getImportManager").invoke(sim);
            String stepPath = "D:\\\\CFD-harness-Windows-StarCCM\\\\scripts\\\\rotor37_extruded.step";
            pw.println("Trying importCaeFile...");
            try {
                Method m = im.getClass().getMethod("importCaeFile", String.class, Class.forName("star.common.Units"), boolean.class);
                try {
                    m.invoke(im, stepPath, null, true);
                    pw.println("  OK (true boolean)");
                } catch (InvocationTargetException ite) {
                    pw.println("  inner exception: " + ite.getCause());
                    ite.getCause().printStackTrace(pw);
                }
            } catch (Throwable t) { pw.println("  reflection FAIL: " + t); }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
