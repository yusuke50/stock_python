import pandas as pandas

grades = {
    "name": ["Mike", "Aby", "Cherry"],
    "Math": [80, 84, 90],
    "English": [90, 65, 93],
}

df = pandas.DataFrame(grades)


print('建立 df:')
print(df)

print('=======')

print(df.at[1, "Math"])
