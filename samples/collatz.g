function void collatz(n:int) {
    print("Starting number: " + n)
    set steps = 0

    while (n != 1) {
        if (n % 2 == 0) {
            n = n / 2
        } else {
            n = n * 3 + 1
        }
        print("Next number: " + n)
        steps++
    }

    print("Collatz Conjecture completed in " + steps + " steps.")
}

set num = input().toInteger()
collatz(num)