# Sieve of Eratosthenes.
fn primes_up_to(limit) {
    let is_prime = [];
    for i in range(limit + 1) { push(is_prime, i >= 2); }

    let p = 2;
    while p * p <= limit {
        if is_prime[p] {
            let multiple = p * p;
            while multiple <= limit {
                is_prime[multiple] = false;
                multiple = multiple + p;
            }
        }
        p = p + 1;
    }

    let result = [];
    for i in range(limit + 1) {
        if is_prime[i] { push(result, i); }
    }
    return result;
}

let found = primes_up_to(50);
print found;
print "count: " + str(len(found));
