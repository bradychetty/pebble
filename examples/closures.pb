# Each call to make_counter creates its own private count.
fn make_counter() {
    let count = 0;
    return fn() {
        count = count + 1;
        return count;
    };
}

let a = make_counter();
let b = make_counter();
a();
a();
print "a: " + str(a());
print "b: " + str(b());

# Functions are values, so they can be passed around.
fn map(f, items) {
    let out = [];
    for item in items { push(out, f(item)); }
    return out;
}

fn adder(n) { return fn(x) { return x + n; }; }

print map(adder(10), [1, 2, 3]);
print map(fn(s) { return s + "!"; }, ["hi", "there"]);
