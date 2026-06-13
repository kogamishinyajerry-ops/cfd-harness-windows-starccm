// EnableModelProbe.java — D-7: 探测 RotatingReferenceFrame 在 STAR-CCM+ 2402 R8
// 是否存在. 纯 Class.forName(name) 反射,no STAR-CCM+ instance needed at compile time.
// 编译: javac -cp "<star-coremodule.jar>;starbase.jar" EnableModelProbe.java
//       (或者不指定 -cp,只要语法 OK 即可;运行时才需要 star.jar)
public class EnableModelProbe {
    public static void main(String[] args) {
        String[] candidates = {
            "star.flow.RotatingReferenceFrame",
            "star.rotor.RotatingReferenceFrame",
            "star.motion.RotatingReferenceFrame",
            "star.rotating.RotatingReferenceFrame"
        };
        int found = 0;
        for (String name : candidates) {
            try {
                Class<?> c = Class.forName(name);
                System.out.println("FOUND: " + name + " -> " + c.getName());
                found++;
            } catch (ClassNotFoundException e) {
                System.out.println("NOT_FOUND: " + name + " -> ClassNotFoundException");
            } catch (Throwable t) {
                System.out.println("ERR: " + name + " -> " + t.getClass().getSimpleName() + ": " + t.getMessage());
            }
        }
        System.out.println("=== SUMMARY: " + found + " / " + candidates.length + " candidate class names resolved on this classpath ===");
    }
}
