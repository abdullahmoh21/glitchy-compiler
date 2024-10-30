// expected output: 7
function int ackermann(m:int, n:int) {
    if (m == 0) {
        return n + 1
    } elif (m > 0 && n == 0) {
        return ackermann(m - 1, 1)
    } else {
        return ackermann(m - 1, ackermann(m, n - 1))
    }
}

// don't want to hang up unittest
set m = 2
set n = 2
print(ackermann(m, n))
