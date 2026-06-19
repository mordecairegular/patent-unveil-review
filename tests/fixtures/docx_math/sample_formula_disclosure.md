# DOCX 数学公式 QA 样例

符号 \(B_{s,t}\)、\(W_{s,\mathrm{self}}\) 和 \(p_{\max}(s)\) 均应写为 Word 可编辑公式。

\[
B_{s,t}=B_{s,t-1}+\eta_{\mathrm{ch}}E_{s,t,\mathrm{ch}}-\frac{E_{s,t,\mathrm{dis}}}{\eta_{\mathrm{dis}}}\tag{1}
\]

\[
B_s^{\min}\leq B_{s,t}\leq B_s^{\max}\tag{2}
\]

\[
W_{s,\mathrm{self}}=\sum_{t=1}^{T}W_{s,t,\mathrm{self}}\tag{3}
\]

\[
p_{\max}(s)=\frac{\sum_{t=1}^{T}W_{s,t,\mathrm{self}}\pi_t}{W_{s,\mathrm{self}}}-f_s\tag{4}
\]

\[
[p_{\min}^{\mathrm{rob}}(s),p_{\max}^{\mathrm{rob}}(s)]=[\max_{k\in\mathcal{K}}p_{\min}^{(k)}(s),\min_{k\in\mathcal{K}}p_{\max}^{(k)}(s)]\tag{5}
\]
