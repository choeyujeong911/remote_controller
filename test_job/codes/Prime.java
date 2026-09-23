public class Prime {
    static boolean isPrime(long n) {
        if (n < 2) return false;
        if (n % 2 == 0) return n == 2;

        for (long d = 3; d <= n / d; d += 2)
            if (n % d == 0)
                return false;

        return true;
    }

    public static void main(String[] args) {
        double target = 310.0;

        long start = System.nanoTime();
        long n = 2;
        long count = 0;
        long lastPrime = 0;

        while ((System.nanoTime() - start) / 1e9 < target) {
            if (isPrime(n)) {
                count++;
                lastPrime = n;
            }
            n++;
        }

        double elapsed = (System.nanoTime() - start) / 1e9;

        System.out.println("workload=prime");
        System.out.println("tested_until=" + n);
        System.out.println("primes=" + count);
        System.out.println("last_prime=" + lastPrime);
        System.out.println("elapsed=" + elapsed + "s");
    }
}