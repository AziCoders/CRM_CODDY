import json

city_name = "Magas_test"

# with open(f'../../data/{city_name}')
with open(f'../../data/{city_name}/students.json', "r", encoding="UTF-8") as f:
    data = json.load(f)
x = 0
for i in data:
    print(data[i])
    print(data[i]["group_name"], data[i]["total_students"])
    x += data[i]["total_students"]
    print()

print(x)