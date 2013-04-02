$('#submitAddToTabForm').click(function (e) {
   $("#addToTabForm").submit(); 
});
function linkTo(url)
{
   document.location.href = url;
};
function toggleSidebarQntForm (e) {
	var pn = $(this).attr('name');
	var hidden_div = '#'+pn+'_chgQntFormSmallWidgetWrapper';
	$(hidden_div).toggle();
};

function showCopyOrderToCartForm (e) {
	$('#copyToCartFormDescription').hide();
	$('#copyToCartForm').show();
};

function toggleNewAddressForm (e) {
	$('#showAddressWrapper').toggle();
	$('#addAddressFormWrapper').toggle();
};
function toggleAddProductForm (e) {
	$('#addProductFormWrapper').toggle();
	$('#shareWrapper').hide();
	$('#embedWrapper').hide();
	$('#forkWrapper').hide();
	$('#detailsWrapper').hide();
	
	$(this).toggleClass("active");
	$('#fcShareButton').removeClass("active");
	$('#fcEmbedButton').removeClass("active");
	$('#fcForkButton').removeClass("active");
	$('#fcDetailsButton').removeClass("active");
};
function toggleCartShare (e) {
	$('#shareWrapper').toggle();
	$('#embedWrapper').hide();
	$('#forkWrapper').hide();
	$('#detailsWrapper').hide();
	$('#addProductFormWrapper').hide();

	$(this).toggleClass("active");
	$('#fcEmbedButton').removeClass("active");
	$('#fcForkButton').removeClass("active");
	$('#fcDetailsButton').removeClass("active");
	$('#fcAddProductButton').removeClass("active");
};
function toggleCartEmbed (e) {
	$('#shareWrapper').hide();
	$('#embedWrapper').toggle();
	$('#forkWrapper').hide();
	$('#detailsWrapper').hide();
	$('#addProductFormWrapper').hide();
	
	$('#fcShareButton').removeClass("active");
	$(this).toggleClass("active");
	$('#fcForkButton').removeClass("active");
	$('#fcDetailsButton').removeClass("active");
	$('#fcAddProductButton').removeClass("active");
};
function toggleCartFork (e) {
	$('#shareWrapper').hide();
	$('#embedWrapper').hide();
	$('#forkWrapper').toggle();
	$('#detailsWrapper').hide();
	$('#addProductFormWrapper').hide();
	
	$('#fcShareButton').removeClass("active");
	$('#fcEmbedButton').removeClass("active");
	$(this).toggleClass("active");
	$('#fcDetailsButton').removeClass("active");
	$('#fcAddProductButton').removeClass("active");
};
function toggleCartDetails (e) {
	$('#shareWrapper').hide();
	$('#embedWrapper').hide();
	$('#forkWrapper').hide();
	$('#detailsWrapper').toggle();
	$('#addProductFormWrapper').hide();
	
	$('#fcShareButton').removeClass("active");
	$('#fcEmbedButton').removeClass("active");
	$('#fcForkButton').removeClass("active");
	$(this).toggleClass("active");
	$('#fcAddProductButton').removeClass("active");
};

$(document).ready(function() {
	// put all your jQuery goodness in here.
	
	$('.toggleChangeQntButton').click(toggleSidebarQntForm);
	$('.toggleChangeQntButtonX').click(toggleSidebarQntForm);
	$('.rowcheckident').click(showCopyOrderToCartForm);
	$('#toggleNewAddressFormButton').click(toggleNewAddressForm);
	$('#toggleNewAddressFormCancel').click(toggleNewAddressForm);
	$('#toggleNewAddressFormX').click(toggleNewAddressForm);
	$('#fcShareButton').click(toggleCartShare);
	$('#fcEmbedButton').click(toggleCartEmbed);
	$('#fcForkButton').click(toggleCartFork);
	$('#fcDetailsButton').click(toggleCartDetails);
	$('#fcAddProductButton').click(toggleAddProductForm);
	
	// Initiaize the tooltips
	$('#toggleWatchlist').tooltip();
	$('#togglePublicCarts').tooltip();
	$('#togglePaidTabs').tooltip();
	$('#toggleAlerts').tooltip();
	$('#moreOptionsButton').tooltip();
	for (var i=0; i<3; i++)
	{
		var mmButtonId = '#mmMoreOptionsButton'+i;
		var cartButtonId = '#cartMoreOptionsButton'+i;
		var wlButtonId = '#wlMoreOptionsButton'+i;
		var pButtonId = '#belistMoreOptionsButton'+i;
		var aButtonId = '#aMoreOptionsButton'+i;
		
		$(mmButtonId).tooltip();
		$(cartButtonId).tooltip();
		$(wlButtonId).tooltip();
		$(pButtonId).tooltip();
		$(aButtonId).tooltip();
		
	}
	
	// Sidebar Menu Button's Toggle Functions
	//////////////////////////////////////////
	$('#toggleCartButton').click(function (e) {
	  $('#cartSidebar').toggle();
		///////////////////////////
		$('#mmOrdersSidebar').hide();
		$('#PublicCartsSidebar').hide();
		$('#watchlistSidebar').hide();
		$('#alertsSidebar').hide();
	});
	$('#toggleCartX').click(function (e) {
	  $('#cartSidebar').toggle();
	});

	//////////////////////////////////////////
	$('#toggleMMOrdersButton').click(function (e) {
		$('#mmOrdersSidebar').toggle();
		///////////////////////////
		$('#cartSidebar').hide();
		$('#PublicCartsSidebar').hide();
		$('#watchlistSidebar').hide();
		$('#alertsSidebar').hide();
	  
	});
	$('#toggleMMOrdersX').click(function (e) {
	  $('#mmOrdersSidebar').toggle();
	});

	//////////////////////////////////////////
	$('#togglePublicCartsButton').click(function (e) {
		$('#PublicCartsSidebar').toggle();
		///////////////////////////
		$('#cartSidebar').hide();
		$('#mmOrdersSidebar').hide();
		$('#watchlistSidebar').hide();
		$('#alertsSidebar').hide();
	});
	$('#togglePublicCartsX').click(function (e) {
	  $('#PublicCartsSidebar').toggle();
	});

	//////////////////////////////////////////
	$('#toggleWatchlistButton').click(function (e) {
		$('#watchlistSidebar').toggle();
		///////////////////////////
		$('#cartSidebar').hide();
		$('#mmOrdersSidebar').hide();
		$('#PublicCartsSidebar').hide();
		$('#alertsSidebar').hide();
	});
	$('#toggleWatchlistX').click(function (e) {
	  $('#watchlistSidebar').toggle();
	});
	
	//////////////////////////////////////////
	$('#toggleAlertsButton').click(function (e) {
		$('#alertsSidebar').toggle();
		///////////////////////////
		$('#cartSidebar').hide();
		$('#mmOrdersSidebar').hide();
		$('#PublicCartsSidebar').hide();
		$('#watchlistSidebar').hide();
	});
	$('#toggleAlertsX').click(function (e) {
	  $('#alertsSidebar').toggle();
	});

});