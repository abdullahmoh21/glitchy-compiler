// expected output: 5.000000

set sumEvens:double = 0.0
set sumOdds:double = 0.0
for (i = 1; i <= 10; i++) {
    if (i % 2 == 0) {
        sumEvens += i
    } else {
        sumOdds += i
    }
}

print(sumEvens-sumOdds)