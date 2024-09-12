# import pytest

# from order_optimization.handler import handle_common
# from django.core.cache import cache
# from django.contrib import messages


# @pytest.mark.django_db
# def test_common_handler(mocker):

#     mock_request = mocker.Mock()
#     mock_request.POST.get.return_value = "file_id_123"

#     mock_results = {"trim": 10.0, "output": [{"cut_width": 5.0, "out": 2, "id": 1}]}

#     mocker.patch.object(cache, "get", return_value=mock_results)
#     mocker.patch.object(cache, "set")
#     mocker.patch("order_optimization.handler.get_orders", return_value=mocker.Mock())
#     mocker.patch(
#         "order_optimization.handler.get_optimizer",
#         return_value=mocker.Mock(
#             fitness_values=-5.0,
#             output=mocker.Mock(to_dict=lambda x: [{"cut_width": 5.0, "out": 2}]),
#         ),
#     )
#     mocker.patch(
#         "order_optimization.handler.get_outputs",
#         return_value=(-5.0, [{"cut_width": 5.0, "out": 2}]),
#     )
#     mocker.patch("order_optimization.handler.set_common", return_value=mock_results)
#     mocker.patch.object(messages, "success")
#     mocker.patch.object(messages, "error")

#     handle_common(mock_request)
    
#     cache.get.assert_called_once_with("optimization_results")
#     messages.success.assert_called_once_with(mock_request, "Common order found.")
