import java.security.MessageDigest;
import java.util.Arrays;

public class Sha256 {
    public static void main(String[] args) throws Exception {
        double target = 310.0;

        byte[] data = new byte[1024 * 1024];
        Arrays.fill(data, (byte)'A');

        MessageDigest md = MessageDigest.getInstance("SHA-256");

        long start = System.nanoTime();
        long count = 0;
        byte[] digest = null;

        while ((System.nanoTime() - start) / 1e9 < target) {
            digest = md.digest(data);

            for (int i = 0; i < data.length; i++)
                data[i] = digest[i % digest.length];

            count++;
        }

        double elapsed = (System.nanoTime() - start) / 1e9;

        StringBuilder hex = new StringBuilder();
        for (byte b : digest)
            hex.append(String.format("%02x", b));

        System.out.println("workload=sha256");
        System.out.println("hashes=" + count);
        System.out.println("digest=" + hex);
        System.out.println("elapsed=" + elapsed + "s");
    }
}