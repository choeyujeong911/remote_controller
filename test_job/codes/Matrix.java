import java.util.Random;

public class Matrix {
    public static void main(String[] args) {
        int n = 250;
        double target = 10.0;

        double[][] a = new double[n][n];
        double[][] b = new double[n][n];
        double[][] c = new double[n][n];

        Random r = new Random(42);

        for (int i = 0; i < n; i++)
            for (int j = 0; j < n; j++) {
                a[i][j] = r.nextDouble();
                b[i][j] = r.nextDouble();
            }

        long start = System.nanoTime();
        int runs = 0;
        double checksum = 0;

        while ((System.nanoTime() - start) / 1e9 < target) {
            for (int i = 0; i < n; i++)
                for (int j = 0; j < n; j++) {
                    double sum = 0;
                    for (int k = 0; k < n; k++)
                        sum += a[i][k] * b[k][j];
                    c[i][j] = sum;
                }

            checksum = 0;
            for (double[] row : c)
                for (double v : row)
                    checksum += v;

            runs++;
        }

        double elapsed = (System.nanoTime() - start) / 1e9;

        System.out.println("workload=matrix");
        System.out.println("runs=" + runs);
        System.out.println("checksum=" + checksum);
        System.out.println("elapsed=" + elapsed + "s");
    }
}