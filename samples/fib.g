// program to calculate the fibonacci of input number
function void fib(n:int) {  
    if (n == 0) {
        print("Fibonacci[0] = 0")
        return
    }
    
    set a = 0
    set b = 1

    for (i = 2; i <= n; i++) {
        set next = a + b      
        a = b
        b = next
    }

    print("Fibonacci[" + (n) + "] = " + b)   
}
print("Please enter an integer:")
set num = input().toInteger()
fib(num)