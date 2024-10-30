// expected output: 271.000000
set a1:double = 4
set b1:double = 3
set c1:double = 10
set d1:double = 25

set a2:double = 8
set b2:double = 5
set c2:double = 3
set d2:double = 7

set a3:double = 10
set b3:double = 2
set c3:double = 4
set d3:double = 5

set a4:double = 5
set b4:double = 4
set c4:double = 12
set d4:double = 8

set a5:double = 1
set b5:double = 2
set c5:double = 3
set d5:double = 4

set result:double = 0

if ((a1 + b1 * 2) > 9 && (c1 * d1 - (c1 * d1 / 4) * 4) == 2 && d1 > a1) {
    result += 1 
}

if ((a2 - (a2 / 3) * 3) == 2 || (b2 * c2) < 50 || (d2 - b2) * 2 == a2) {
    result += 2 
}

if ((d3 + a3 > c3 * 2) && (b3 - 1 == a3 / 10) && (c3 != d3)) {
    result += 3 
} else {
    print("The third if expression evaluated to false, please check why")
}

if ((a4 * c4 == 24 || d4 / b4 == 2) && (c4 - d4 < a4)) {
    result += 4 
} else {
    print("The fourth if expression evaluated to false, please check why")
}

if ((a5 + b5 * 2) > 10 && (c5 * d5 - (c5 * d5 / 4) * 4) == 0 && d5 > a5) {
    result += 5 
} elif ((a5 - (a5 / 3) * 3) == 2 || (b5 * c5) < 50 || (d5 - b5) * 2 == a5) {
    result += 6 
} elif ((d5 + a5 > c5 * 2) && (b5 - 1 == a5 / 10) && (c5 != d5)) {
    result += 7 
} elif ((a5 * c5 == 24 || d5 / b5 == 2) && (c5 - d5 < a5)) {
    result += 8 
} else {
    result += 9 
}

result += 2^8
print(result)