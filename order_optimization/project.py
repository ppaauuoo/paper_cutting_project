# %%
from .modules.ordplan import ORD
from .modules.ga import GA
from .modules.lp import LP

# roll_paper = [68, 73, 75, 79, 82, 85, 88, 91, 95, 97]
# deadline_scope = เลขrowกำหนดส่งที่จะยึดใช้ ex 0 = 5/1/2023
# deadline = จะยึดจาก scope หรือไม่ ถ้า False คือเอาทั้งหมดเลย
orders = ORD("data/true_ordplan.csv", deadline_scope=0).get(deadline=False)
orders

# %% [markdown]
# กำหนดข้อมูล

# %% [markdown]
# หา roll
#

# %%
tuning_value = 3  # ค่าหาร roll ถ้า order น้อยเกิน โอกาศหา roll เหมาะสมยาก
for i, width in enumerate(orders["ตัดกว้าง"]):  # ลูปwidth
    roll = ORD.calculate_roll_tuning(width, tuning_value)  # โยน width ไปเทียบหา roll
    if roll:
        print(f"using roll: {roll}, founded at: {width}")
        break

# %%
ga_instance = GA(orders, size=73, tuning_values=2, num_generations=50).get()
ga_instance.run()

# %%
#ga_instance.plot_fitness()

# %%
# lp_instance = LP(orders,roll,tuning_value).run()
