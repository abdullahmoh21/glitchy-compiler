// expected output: 1047.000000
function double power(base:double, exponent:double) {
    set result:double = 1.0
    for (i = 1; i <= exponent; i++) {
        result = result * base
    }
    return result
}

set base = 2.0
set exponent = 10.0
set result = base^exponent + (power(3.0, 3) - power(2.0, 2))
print(result)