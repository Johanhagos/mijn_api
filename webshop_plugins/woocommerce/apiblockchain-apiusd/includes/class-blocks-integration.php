<?php
/**
 * Registers "Pay with APIUSD" with WooCommerce's block checkout. Payment itself still runs
 * through WC_Gateway_APIBlockchain_APIUSD::process_payment (redirect to the hosted checkout).
 */

if (!defined('ABSPATH')) {
    exit;
}

use Automattic\WooCommerce\Blocks\Payments\Integrations\AbstractPaymentMethodType;

final class APIBlockchain_APIUSD_Blocks_Integration extends AbstractPaymentMethodType {

    protected $name = 'apiblockchain_apiusd';

    public function initialize() {
        $this->settings = get_option('woocommerce_apiblockchain_apiusd_settings', array());
    }

    public function is_active() {
        $gateway = apiblockchain_apiusd_gateway();
        return $gateway ? $gateway->is_available() : false;
    }

    public function get_payment_method_script_handles() {
        wp_register_script(
            'apiblockchain-apiusd-blocks',
            plugins_url('assets/checkout-blocks.js', APIBLOCKCHAIN_APIUSD_FILE),
            array('wc-blocks-registry', 'wc-settings', 'wp-element', 'wp-html-entities'),
            '1.0.0',
            true
        );
        return array('apiblockchain-apiusd-blocks');
    }

    public function get_payment_method_data() {
        return array(
            'title'       => $this->get_setting('title') ?: 'Pay with APIUSD',
            'description' => $this->get_setting('description'),
            'supports'    => array('products'),
        );
    }
}
