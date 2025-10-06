// A simple transformer for CSS files that prevents processing
module.exports = {
  process() {
    return {
      code: 'export default "";',
      map: null
    }
  }
}