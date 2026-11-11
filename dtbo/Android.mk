#
# GQ5012BF1 source-built DTBO (LIEPPOS_DTBO=source, see BoardConfig.mk and
# dtbo/README.md). In stock mode this file only reports the choice.
#
LOCAL_PATH := $(call my-dir)

ifeq ($(TARGET_DEVICE),gq5012bf1)

ifeq ($(LIEPPOS_DTBO),source)

LIEPPOS_DTBO_KDTS := $(LIEPPOS_KERNEL_SOURCE)/arch/arm64/boot/dts
ifeq ($(wildcard $(LIEPPOS_DTBO_KDTS)/mediatek/gq5012bf1.dts),)
  $(error LIEPPOS_DTBO=source but $(LIEPPOS_DTBO_KDTS)/mediatek/gq5012bf1.dts does not exist; set LIEPPOS_KERNEL_SOURCE (no fallback to the stock image))
endif

# Inputs: the board overlay, its includes and the binding headers it uses.
LIEPPOS_DTBO_INPUTS := \
    $(wildcard $(LIEPPOS_DTBO_KDTS)/mediatek/gq5012bf1.dts \
               $(LIEPPOS_DTBO_KDTS)/mediatek/gq5012bf1-*.dtsi \
               $(LIEPPOS_DTBO_KDTS)/gq5012bf1/*.dtsi \
               $(LIEPPOS_KERNEL_SOURCE)/include/dt-bindings/pinctrl/mt6878-pinfunc.h \
               $(LIEPPOS_KERNEL_SOURCE)/include/dt-bindings/pinctrl/mt65xx.h \
               $(LIEPPOS_KERNEL_SOURCE)/include/dt-bindings/clock/mt6878-clk.h \
               $(LIEPPOS_KERNEL_SOURCE)/include/dt-bindings/interrupt-controller/irq.h \
               $(LIEPPOS_KERNEL_SOURCE)/include/dt-bindings/interrupt-controller/arm-gic.h \
               $(LIEPPOS_KERNEL_SOURCE)/include/dt-bindings/phy/phy.h) \
    $(LOCAL_PATH)/build-dtbo.sh \
    $(LOCAL_PATH)/dtbo_tool.py \
    $(LOCAL_PATH)/../prebuilt/dtbo.img

LIEPPOS_DTBO_CLANG := $(LLVM_PREBUILTS_BASE)/$(BUILD_OS)-x86/$(LLVM_PREBUILTS_VERSION)/bin/clang

$(BOARD_PREBUILT_DTBOIMAGE): PRIVATE_KSRC := $(LIEPPOS_KERNEL_SOURCE)
$(BOARD_PREBUILT_DTBOIMAGE): PRIVATE_SCRIPT := $(LOCAL_PATH)/build-dtbo.sh
$(BOARD_PREBUILT_DTBOIMAGE): PRIVATE_STOCK := $(LOCAL_PATH)/../prebuilt/dtbo.img
$(BOARD_PREBUILT_DTBOIMAGE): PRIVATE_CPP := $(LIEPPOS_DTBO_CLANG) -E
$(BOARD_PREBUILT_DTBOIMAGE): PRIVATE_FLAGS := $(if $(filter true,$(LIEPPOS_DTBO_ALLOW_UNSIGNED)),--allow-unsigned)
$(BOARD_PREBUILT_DTBOIMAGE): $(LIEPPOS_DTBO_INPUTS) $(HOST_OUT_EXECUTABLES)/dtc \
        $(HOST_OUT_EXECUTABLES)/mkdtboimg $(LIEPPOS_DTBO_CLANG)
	@echo "LieppOS DTBO: building from source $(PRIVATE_KSRC)"
	$(hide) rm -rf $(dir $@) && mkdir -p $(dir $@)
	$(hide) $(PRIVATE_SCRIPT) --kernel-src $(PRIVATE_KSRC) --out $(dir $@) \
	    --stock $(PRIVATE_STOCK) --dtc $(HOST_OUT_EXECUTABLES)/dtc \
	    --cpp "$(PRIVATE_CPP)" --mkdtboimg $(HOST_OUT_EXECUTABLES)/mkdtboimg \
	    $(PRIVATE_FLAGS)

$(info LieppOS DTBO: SOURCE-BUILT from $(LIEPPOS_DTBO_KDTS)/mediatek/gq5012bf1.dts)

else  # stock

$(info LieppOS DTBO: STOCK prebuilt $(BOARD_PREBUILT_DTBOIMAGE))

endif

# $(PRODUCT_OUT)/lieppos-dtbo-report.txt records which DTBO the build used.
LIEPPOS_DTBO_REPORT := $(PRODUCT_OUT)/lieppos-dtbo-report.txt
$(LIEPPOS_DTBO_REPORT): PRIVATE_MODE := $(LIEPPOS_DTBO)
$(LIEPPOS_DTBO_REPORT): PRIVATE_IMG := $(BOARD_PREBUILT_DTBOIMAGE)
$(LIEPPOS_DTBO_REPORT): $(BOARD_PREBUILT_DTBOIMAGE)
	$(hide) mkdir -p $(dir $@)
	$(hide) if [ "$(PRIVATE_MODE)" = source ]; then \
	    cp $(dir $(PRIVATE_IMG))BUILD-REPORT.txt $@; \
	else \
	    echo "LIEPPOS_DTBO_SOURCE=stock" > $@; \
	    echo "dtbo_img=$(PRIVATE_IMG) sha256 $$(sha256sum $(PRIVATE_IMG) | cut -d' ' -f1)" >> $@; \
	fi
droidcore-unbundled: $(LIEPPOS_DTBO_REPORT)

endif
