int factorial(int n) {
  if (n <= 1)
    return 1;
  return n * factorial(n - 1);
}

int fibonacci(int n) {
  if (n == 0)
    return 0;
  if (n == 1)
    return 1;
  int a = 0;
  int b = 1;
  int i = 2;
  while (i <= n) {
    int temp = a + b;
    a = b;
    b = temp;
    i++;
  }
  return b;
}

int main() {
  int x = 10;
  int y = 3;
  int z = x * y + 2;
  float pi = 3.14159;
  float area = pi * x * x;
  char letra = 'A';
  int hex_val = 0xFF;
  int oct_val = 017;
  int arr[5];
  int i = 0;
  for (i = 0; i < 5; i++) {
    arr[i] = i * i;
  }
  if (x >= y && z != 0) {
    x += y;
    y -= 1;
  } else {
    x = y % 2;
  }
  int bits = x << 2;
  bits |= 0x0F;
  bits &= ~y;
  int ternario = (x > y) ? x : y;
  return 0;
}
