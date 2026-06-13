import star.common.*;
import star.base.neo.*;
import java.io.*;
import java.lang.reflect.*;
import java.util.*;

public class ProbeImportMgr extends StarMacro {
    public void execute() {
        Simulation sim = getActiveSimulation();
        PrintWriter pw = null;
        try { pw = new PrintWriter(new FileWriter("D:\\\\CFD-harness-Windows-StarCCM\\\\probe_import_mgr.log")); } catch (Throwable t) { return; }
        try {
            Class<?> imCls = Class.forName("star.common.ImportManager");
            pw.println("=== ImportManager ALL methods ===");
            for (Method m : imCls.getMethods()) {
                String n = m.getName();
                String ps = java.util.Arrays.toString(m.getParameterTypes());
                if (ps.length() < 110) pw.println("  " + n + "(" + ps + ") -> " + m.getReturnType().getSimpleName());
            }
        } catch (Throwable t) { pw.println("FATAL: " + t); }
        pw.close();
    }
}
