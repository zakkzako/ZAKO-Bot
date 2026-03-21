#!/bin/bash

# .pyファイルのリストを表示し、最後に合計サイズを計算する
echo "--- Python Files List ---"
find . -name "*.py" -type f -exec du -ch {} + | grep -v "total$"

echo "--------------------------"
echo -n "Total Size: "
find . -name "*.py" -type f -print0 | xargs -0 du -ch | tail -n 1 | cut -f 1
