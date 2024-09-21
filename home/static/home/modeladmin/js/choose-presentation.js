$(document).ready(function () {
    // Replace 'id_field_name' with the actual name of your SnippetChooserPanel field

    $('#id_modello_presentazione').on('change', function () {
        const id = $(this).val();
        alert(id)

    })

    if (location.href.indexOf('admin/snippets/home/listino/') > -1) {
        $('a[href="/admin/snippets/home/listino/add/"]').attr('href', '/admin/add-listino')
    }
});