/**
 * Sample file with various code quality issues for testing
 */

// Complex function with high cyclomatic complexity
function complexFunction(a, b, c, d, e, f) {
  let result = 0;

  if (a > 0) {
    if (b > 0) {
      if (c > 0) {
        if (d > 0) {
          if (e > 0) {
            if (f > 0) {
              result = a + b + c + d + e + f;
            } else {
              result = a + b + c + d + e;
            }
          } else {
            result = a + b + c + d;
          }
        } else {
          result = a + b + c;
        }
      } else {
        result = a + b;
      }
    } else {
      result = a;
    }
  }

  for (let i = 0; i < 100; i++) {
    if (i % 2 === 0) {
      result += i;
    } else if (i % 3 === 0) {
      result += i * 2;
    } else {
      result += i * 3;
    }
  }

  return result;
}

// Long function
function veryLongFunction() {
  let data = [];
  for (let i = 0; i < 100; i++) {
    data.push(i);
    data.push(i * 2);
    data.push(i * 3);
    data.push(i * 4);
    data.push(i * 5);
    data.push(i * 6);
    data.push(i * 7);
    data.push(i * 8);
    data.push(i * 9);
    data.push(i * 10);
  }

  let result = 0;
  for (const item of data) {
    result += item;
  }

  let processed = [];
  for (const item of data) {
    processed.push(item * 2);
  }

  let filtered = [];
  for (const item of processed) {
    if (item > 100) {
      filtered.push(item);
    }
  }

  let transformed = [];
  for (const item of filtered) {
    transformed.push({
      value: item,
      doubled: item * 2,
      tripled: item * 3
    });
  }

  return transformed;
}

// Duplicated code
function processDataA(data) {
  let result = [];
  for (const item of data) {
    if (item > 10) {
      result.push(item * 2);
    }
  }
  return result;
}

function processDataB(data) {
  let result = [];
  for (const item of data) {
    if (item > 10) {
      result.push(item * 2);
    }
  }
  return result;
}

// Simple function with good quality
function simpleCalculation(x, y) {
  return x + y * 2;
}

// Good function example
function formatDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export {
  complexFunction,
  veryLongFunction,
  processDataA,
  processDataB,
  simpleCalculation,
  formatDate
};
