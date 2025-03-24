from django import forms
from .models import ProductReview

class ProductReviewForm(forms.ModelForm):
    """Form for submitting product reviews."""
    class Meta:
        model = ProductReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '5'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': '3',
                'placeholder': 'Write your review here...'
            })
        }
