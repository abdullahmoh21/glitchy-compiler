// expected output: 6
function int gcd(a:int, b:int) {
    if (b == 0) {
        return a
    }
    return gcd(b, a % b)
}

set result = gcd(54, 24)
print(result)