# Recursion, then the same result with a loop.
fn fib(n) {
    if n < 2 { return n; }
    return fib(n - 1) + fib(n - 2);
}

fn fib_loop(n) {
    let a = 0;
    let b = 1;
    for _ in range(n) {
        let next = a + b;
        a = b;
        b = next;
    }
    return a;
}

for n in [0, 1, 2, 10, 20] {
    print "fib(" + str(n) + ") = " + str(fib(n));
}
print fib_loop(90);
