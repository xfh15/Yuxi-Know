/** 判断键盘事件是否仍属于输入法组合输入，兼容仍使用 229 标记的浏览器。 */
export const isImeComposing = (event) => event.isComposing || event.keyCode === 229
