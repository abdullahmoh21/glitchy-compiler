// expected output: 305.000000
set a:double = 10
set b:double = 20
set c:double = 30
set d:double = 40
set result = 0.0


if ((a + b) > 25 && (c - b) < 15) {
    result = (a * b) + (c / d)
} elif ((a - b) < 0 || (c + d) > 50) {
    result = (a + b + c + d) * 2
} else {
    result = 0
}

for (i = 1; i <= 5; i++) {
    if (i % 2 == 0) {
        result += i * 10
    } else {
        result += i * 5
    }
}

print(result)
