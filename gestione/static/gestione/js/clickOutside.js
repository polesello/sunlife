// directives/clickOutside.js
export default {
    beforeMount(el, binding) {
      el.clickOutsideEvent = (event) => {
        // Check if the clicked element is outside the target element
        if (!(el === event.target || el.contains(event.target))) {
          // If it is, call the provided method
          binding.value(event);
        }
      };
      // Attach the event listener to the document
      document.addEventListener('click', el.clickOutsideEvent);
    },
    unmounted(el) {
      // Remove the event listener when the element is unmounted
      document.removeEventListener('click', el.clickOutsideEvent);
    },
  };