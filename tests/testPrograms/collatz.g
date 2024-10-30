// expected 111
function void collatz(n:int) {
    set steps = 0

    while (n != 1) {
        if (n % 2 == 0) {
            n = n / 2
        } else {
            n = n * 3 + 1
        }
        steps++
    }

    print(steps)
}


collatz(1000)
