// highly recursive 
function int ackermann(m:int, n:int) {
    print("Ackermann called!")
    if (m == 0) {
        return n + 1
    } elif (m > 0 && n == 0) {
        return ackermann(m - 1, 1)
    } else {
        return ackermann(m - 1, ackermann(m, n - 1))
    }
}

print("Enter a value for m: ")
set m = input().toInteger()
print("Enter a value for n: ")
set n = input().toInteger()

print("Ackermann(" + m + ", " + n + ") = " + ackermann(m, n))
