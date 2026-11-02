import fs from 'node:fs/promises';
const dir='C:/Users/qiwen/Desktop/study/mbti/outputs/qwen25_05b_20261026';
await fs.mkdir(dir,{recursive:true});
let s=await fs.readFile('C:/Users/qiwen/Desktop/study/mbti/outputs/opt125m_20261026/build.mjs','utf8');
s=s.replaceAll('new_exp/opt125m','new_exp/qwen25_05b').replaceAll('outputs/opt125m_20261026','outputs/qwen25_05b_20261026').replaceAll('OPT-125M 实验测试结果','Qwen2.5-0.5B 实验测试结果').replaceAll('OPT125M_实验结果汇总.xlsx','QWEN25_05B_实验结果汇总.xlsx').replaceAll('c.opt_model_path','c.qwen_model_path').replace('12,14,26,10,13,13,21','12,18,65,10,13,13,21');
s=s.replace('wb.recalculate();',`sum.getRange('A24').values=[['LLM 层数：HZMETRO 为 12，BJMETRO 为 2，其余为 1；详细配置见数据集与配置。']];\nwb.recalculate();`);
s=s.replace("'A1:L23','summary'","'A1:L24','summary'").replace("['数据集与配置','A1:B16','datasets']","['数据集与配置','A1:D16','datasets'],['数据集与配置','L5:U16','model_config']");
await fs.writeFile(`${dir}/build.mjs`,s);
