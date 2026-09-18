# Quicksort written without mutating its input.
fn quicksort(items) {
    if len(items) <= 1 { return items; }

    let pivot = items[0];
    let smaller = [];
    let larger = [];
    for i in range(1, len(items)) {
        if items[i] < pivot {
            push(smaller, items[i]);
        } else {
            push(larger, items[i]);
        }
    }

    let result = quicksort(smaller);
    push(result, pivot);
    for x in quicksort(larger) { push(result, x); }
    return result;
}

print quicksort([5, 3, 8, 1, 9, 2, 7]);
print quicksort(["pear", "apple", "fig"]);
print quicksort([]);
