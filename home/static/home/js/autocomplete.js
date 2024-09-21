
// $(document).ready(function() {
//     $('.w-field--wagtail_select2_text_input input').select2({
//         ajax: {
//           url: '/prodotti/search/',
//           dataType: 'json'
//         }
//       })
// })

$(document).ready(function() {

// $('.offerta-form').on('focus', '.autocomplete[name$=codice]', function() {
//     $(this).autocomplete({
//         source: "/listini/search?field=codice",
//         minLength: 2,
//         select: function(event, ui) {
//             var row = $(this).closest('tr');
//             var prezzo_field = row.find('input[name$=prezzo]');
//             var descrizione_field = row.find('textarea[name$=descrizione]');

//             prezzo_field.val(ui.item.prezzo).trigger('input');
//             descrizione_field.val(ui.item.descrizione);

//         }
//     })
// })


// Serve event delegation, in modo che funzioni anche su elementi da aggiungere






// const queryInput = document.querySelector("#query");

// const awesomplete = new Awesomplete(queryInput, {
//   filter: () => { // We will provide a list that is already filtered ...
//     return true;
//   },
//   sort: false,    // ... and sorted.
//   list: []
// });

// queryInput.addEventListener("input", (event) => {
//   const inputText = event.target.value;
//   // Process inputText as you want, e.g. make an API request.
//   awesomplete.list = ["my"+inputText, "custom"+inputText, "list"+inputText];
//   awesomplete.evaluate();
// });

var inputs = document.querySelectorAll(".awesomplete");
  console.log(inputs)
  $(inputs).each(function() {
    var awesomplete = new Awesomplete(this);
  
    $(this).on("input", function() {
      var input = this;
      console.log(this.value)
      $.ajax({
        url: "/prodotti/search/?field=codice",
        method: "GET",
        data: { term: input.value },
        success: function(data) {
          awesomplete.list = data;
        }
      });
    });

    this.addEventListener("awesomplete-select", e => {
        this.value = e.text.value

        const textarea = this.closest('.w-panel__content').querySelector('textarea[name$=descrizione]')
        textarea.value = e.text.label.split('•')[1].trim()
    });



  });



$('.w-field--wagtail_select2_text_input input').on('input', function() {
 
    // $(this).autocomplete({
    //     source: "/prodotti/search/?field=codice",
    //     minLength: 3,
    //     select: function(event, ui) {
    //         var row = $(this).closest('tr');
    //         var prezzo_field = row.find('input[name$=prezzo]');
    //         var codice_field = row.find('input[name$=codice]');

    //         prezzo_field.val(ui.item.prezzo).trigger('input');
    //         codice_field.val(ui.item.codice);

    //     }
    // })    
})

})